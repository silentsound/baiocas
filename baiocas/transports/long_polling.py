from simplejson import loads
from twisted.internet import reactor
from twisted.internet.defer import Deferred
from twisted.web.client import Agent
from twisted.web.http_headers import Headers

from .. import errors
from http import HttpTransport
from util import MessageConsumer, MessageProducer


class LongPollingHttpTransport(HttpTransport):

    def __init__(self, *args, **kwargs):
        super(LongPollingHttpTransport, self).__init__(*args, **kwargs)
        self._agent = Agent(reactor)
        self._append_message_type = False
        self._requests = []

    @property
    def name(self):
        return 'long-polling'

    def _cancel_request(self, request, messages):
        if request.called:
            return
        self.log.debug('Timeout triggered, cancelling pending request')
        request.cancel()
        self._client.fail_messages(messages, errors.TimeoutError())

    def _cleanup_request(self, result, request, timeout):
        if request in self._requests:
            self.log.debug('Removing completed request')
            self._requests.remove(request)
        if timeout and not timeout.called:
            self.log.debug('Cancelling request timeout')
            timeout.cancel()
        return result

    def _handle_failure(self, failure, messages):
        self.log.debug('Failed to send messages: %s' % failure)
        self._client.fail_messages(messages, errors.CommunicationError(failure.value))
        return None

    def _handle_response(self, response, messages):
        self.log.debug('Received response: %s %s' % (response.code, response.phrase))
        for header, values in response.headers.getAllRawHeaders():
            self.log.debug('Response header %s: %s' % (header, '; '.join(values)))
        if response.code >= 400:
            raise errors.ServerError(response.code, response.phrase)
        finished = Deferred()
        finished.addCallback(self._handle_response_finished, response)
        finished.addErrback(self._handle_failure, messages)
        response.deliverBody(MessageConsumer(finished))
        return response

    def _handle_response_finished(self, messages, response):
        self.update_cookies(
            response.headers.getRawHeaders('Set-Cookie', []),
            time_received=response.headers.getRawHeaders('Date')
        )
        self._client.receive_messages(messages)
        return messages

    def _set_url(self, url):
        super(LongPollingHttpTransport, self)._set_url(url)
        self._append_message_type = (
            len(self.parsed_url.scheme.strip()) > 0 and
            len(self.parsed_url.netloc.strip()) > 0 and
            len(self.parsed_url.query.strip()) == 0 and
            len(self.parsed_url.fragment.strip()) == 0
        )

    def abort(self):
        super(LongPollingHttpTransport, self).abort()
        self.log.debug('Cancelling %d pending requests' % len(self._requests))
        for request in self._requests:
            request.cancel()
        self._requests = []

    def accept(self, bayeux_version):
        return True

    def send(self, messages):

        # Determine the URL for the messages
        url = self.url
        if self._append_message_type and len(messages) == 1 and messages[0].channel.is_meta():
            message_type = '/'.join(messages[0].channel.parts()[1:])
            if not url.endswith('/'):
                url += '/'
            url += message_type

        # Get the headers for the request
        headers = Headers(self.get_headers())
        for header, values in headers.getAllRawHeaders():
            self.log.debug('Request header %s: %s' % (header, '; '.join(values)))

        # Send the request
        self.log.debug('Sending message to %s' % url)
        request = self._agent.request(
            'POST',
            url,
            headers=headers,
            bodyProducer=MessageProducer(messages)
        )
        self._requests.append(request)

        # Set up the timeout
        timeout = reactor.callLater(
            self.get_timeout(messages) / 1000.0,
            self._cancel_request,
            request,
            messages
        )

        # Set up the callbacks
        request.addBoth(self._cleanup_request, request, timeout)
        request.addCallback(self._handle_response, messages)
        request.addErrback(self._handle_failure, messages)
