from email.utils import mktime_tz, parsedate_tz
from twisted.internet.defer import succeed
from twisted.internet.protocol import Protocol
from twisted.web.client import ResponseDone
from twisted.web.http import PotentialDataLoss
from twisted.web.iweb import IBodyProducer
from zope.interface import implements
import logging
import time

from .. import errors
from ..message import Message


def is_cookie_expired(cookie):
    value = None
    if cookie['max-age']:
        value = cookie['max-age']
    elif cookie['expires']:
        value = cookie['expires']
    if not value:
        return False
    if value.isdigit():
        time_received = getattr(cookie, 'time_received', time.time())
        expires = time_received + int(value)
    else:
        expires = parsedate_tz(value)
        if expires:
            expires = mktime_tz(expires)
    if expires and expires <= time.time():
        return True
    return False


class MessageProducer(object):

    # Used by twisted.web.client.Agent to provide request bodies
    implements(IBodyProducer)

    def __init__(self, messages):
        self.log = logging.getLogger('%s.%s' % (self.__module__, self.__class__.__name__))
        self.body = Message.to_json(messages, encoding='utf8')
        self.length = len(self.body)
        self.log.debug('Request body (length: %d): %s' % (self.length, self.body))

    def startProducing(self, consumer):
        consumer.write(self.body)
        return succeed(None)

    def pauseProducing(self):
        pass

    def stopProducing(self):
        pass


class MessageConsumer(Protocol):

    # To prevent buffer overflows, limit responses to 10 MB (in bytes)
    MAXIMUM_SIZE = 10485760

    def __init__(self, finished):
        self.log = logging.getLogger('%s.%s' % (self.__module__, self.__class__.__name__))
        self._finished = finished
        self._remaining = self.MAXIMUM_SIZE
        self._buffer = []

    def dataReceived(self, bytes):
        if not self._remaining:
            self.log.debug('Discarding %d bytes, over buffer limit' % len(bytes))
            return
        bytes = bytes[:self._remaining]
        self._buffer += bytes
        self._remaining -= len(bytes)
        self.log.debug('Received %d bytes, remaining = %d' % (len(bytes), self._remaining))

    def connectionLost(self, failure):
        if not failure.check(PotentialDataLoss, ResponseDone):
            exception = errors.CommunicationError(transport_exception=failure)
            self._finished.errback(exception)
            return
        value = ''.join(self._buffer)
        self.log.debug('Received body: %s' % value)
        self._finished.callback(Message.from_json(value, encoding='utf8'))
