from __future__ import absolute_import
from __future__ import unicode_literals

from tornado import gen
from tornado.curl_httpclient import CurlAsyncHTTPClient
from tornado.httpclient import HTTPClient
from tornado.httpclient import HTTPError
from tornado.httpclient import HTTPRequest
from tornado.httputil import HTTPHeaders

from baiocas import errors
from baiocas.message import Message
from baiocas.transports.http import HttpTransport


class LongPollingHttpTransport(HttpTransport):

    def __init__(self, *args, **kwargs):
        super(LongPollingHttpTransport, self).__init__(*args, **kwargs)
        self._append_message_type = False
        self._create_http_clients()

    @property
    def name(self):
        return 'long-polling'

    def _reset_http_clients(self):
        self._http_client.close()
        self._blocking_http_client.close()
        self._create_http_clients()

    def _create_http_clients(self):
        self._http_client = CurlAsyncHTTPClient(io_loop=self.io_loop)
        self._blocking_http_client = HTTPClient(
            async_client_class=CurlAsyncHTTPClient
        )

    def _handle_response(self, response, messages):

        # Log the received response code and headers
        self.log.debug('Received response: %s' % response.code)
        for header, value in response.headers.get_all():
            self.log.debug('Response header %s: %s' % (header, value))

        # If there was an error, report the sent messages as failed
        if response.error:
            if isinstance(response.error, HTTPError):
                if response.error.code == 599:
                    error = errors.TimeoutError()
                else:
                    error = errors.ServerError(response.error.code)
            else:
                error = errors.CommunicationError(response.error)
            self.log.debug('Failed to send messages: %s' % error)
            self._client.fail_messages(messages, error)
            return

        # Update the cookies
        self.update_cookies(
            response.headers.get_list('Set-Cookie'),
            time_received=response.headers.get('Date')
        )

        # Get the received messages
        self.log.debug('Received body: %s' % response.body)
        messages = Message.from_json(response.body, encoding='utf8')
        self._client.receive_messages(messages)

    def _prepare_request(self, messages):

        # Determine the URL for the messages
        url = self.url
        if self._append_message_type and len(messages) == 1 and messages[0].channel.is_meta():
            message_type = '/'.join(messages[0].channel.parts()[1:])
            if not url.endswith('/'):
                url += '/'
            url += message_type

        # Get the headers for the request
        headers = HTTPHeaders()
        for header, values in self.get_headers().items():
            for value in values:
                headers.add(header, value)
        for header, value in headers.get_all():
            self.log.debug('Request header %s: %s' % (header, value))

        # Get the body for the request
        body = Message.to_json(messages, encoding='utf8')
        self.log.debug('Request body (length: %d): %s' % (len(body), body))

        # Get the timeout (in seconds)
        timeout = self.get_timeout(messages) / 1000.0
        self.log.debug('Request timeout: %ss' % timeout)

        # Build and return the request
        return HTTPRequest(
            url,
            method='POST',
            headers=headers,
            body=body,
            connect_timeout=timeout,
            request_timeout=timeout
        )

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
        self.log.debug('Cancelling pending requests')
        self._reset_http_clients()

    def accept(self, bayeux_version):
        return True

    @gen.coroutine
    def send(self, messages, sync=False):
        request = self._prepare_request(messages)

        # Send the message. For synchronous requests, the Tornado client doesn't
        # return the actual response object if there is an error even though it
        # generates it internally. Instead of recreating it, we'll grab it.
        self.log.debug('Sending message to %s' % request.url)
        if sync:
            try:
                response = self._blocking_http_client.fetch(request)
            except HTTPError:
                response = self._blocking_http_client._response
        else:
            response = yield gen.Task(self._http_client.fetch, request)

        # Handle the response. We catch all exceptions here so that a bad
        # response doesn't end up crashing the Tornado async framework.
        try:
            self._handle_response(response, messages)
        except Exception as ex:
            error = errors.CommunicationError(ex)
            self.log.debug('Exception handling response: %s' % error)
            self._client.fail_messages(messages, error)
