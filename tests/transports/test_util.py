from Cookie import Morsel
from cStringIO import StringIO
from email.utils import formatdate
from mock import patch
from twisted.internet.defer import Deferred
from twisted.python.failure import Failure
from twisted.web.client import ResponseDone
from twisted.web.error import Error
from twisted.web.http import NOT_FOUND, PotentialDataLoss
from unittest import TestCase
import logging
import time

from baiocas import errors
from baiocas.message import Message
from baiocas.transports.util import is_cookie_expired, MessageConsumer, MessageProducer


class TestExpiredCookie(TestCase):

    def setUp(self):
        self.cookie = Morsel()
        self.cookie.set('foo', 'bar', 'bar')
        self.cookie.time_received = time.time() - 1

    def test_no_expiration_information(self):
        assert not is_cookie_expired(self.cookie)

    def test_valid_max_age(self):
        self.cookie['max-age'] = '86400'
        assert not is_cookie_expired(self.cookie)

    def test_valid_max_age_missing_time_received(self):
        self.cookie['max-age'] = '1'
        del self.cookie.time_received
        assert not is_cookie_expired(self.cookie)

    def test_expired_max_age(self):
        self.cookie['max-age'] = '1'
        assert is_cookie_expired(self.cookie)
        self.cookie['max-age'] = '0'
        assert is_cookie_expired(self.cookie)

    def test_expired_max_age_missing_time_received(self):
        self.cookie['max-age'] = '0'
        del self.cookie.time_received
        assert is_cookie_expired(self.cookie)
        self.cookie['max-age'] = '1'
        assert not is_cookie_expired(self.cookie)

    def test_invalid_max_age(self):
        self.cookie['max-age'] = 'invalid'
        assert not is_cookie_expired(self.cookie)

    def test_valid_expires(self):
        self.cookie['expires'] = formatdate(time.time() + 86400, localtime=True)
        assert not is_cookie_expired(self.cookie)

    def test_expired_expires(self):
        self.cookie['expires'] = formatdate(usegmt=True)
        assert is_cookie_expired(self.cookie)

    def test_invalid_expires(self):
        self.cookie['expires'] = 'invalid'
        assert not is_cookie_expired(self.cookie)

    def test_valid_max_age_and_expired_expires(self):
        self.cookie['max-age'] = '86400'
        self.cookie['expires'] = formatdate(usegmt=True)
        assert not is_cookie_expired(self.cookie)

    def test_expired_max_age_and_valid_expires(self):
        self.cookie['max-age'] = '1'
        self.cookie['expires'] = formatdate(time.time() + 86400, localtime=True)
        assert is_cookie_expired(self.cookie)


class TestMessageProducer(TestCase):

    def setUp(self):
        self.messages = [
            Message(channel='/test', id='1'),
            Message(channel='/test', id='2', data='dummy')
        ]
        self.messages_as_json = Message.to_json(self.messages)
        self.producer = MessageProducer(self.messages)

    def test_init(self):
        assert isinstance(self.producer.log, logging.Logger)
        assert self.producer.log.name == 'baiocas.transports.util.MessageProducer'
        assert self.producer.body == self.messages_as_json
        assert self.producer.length == len(self.messages_as_json)

    def test_startProducing(self):
        buffer = StringIO()
        deferred = self.producer.startProducing(buffer)
        assert buffer.getvalue() == self.messages_as_json
        assert deferred.called
        assert deferred.result is None

    def test_pauseProducing(self):
        buffer = StringIO()
        deferred = self.producer.startProducing(buffer)
        self.producer.pauseProducing()
        assert buffer.getvalue() == self.messages_as_json
        assert deferred.called
        assert deferred.result is None

    def test_stopProducing(self):
        buffer = StringIO()
        deferred = self.producer.startProducing(buffer)
        self.producer.stopProducing()
        assert buffer.getvalue() == self.messages_as_json
        assert deferred.called
        assert deferred.result is None


class TestMessageConsumer(TestCase):

    def setUp(self):
        self.deferred = Deferred()
        self.consumer = MessageConsumer(self.deferred)

    def test_init(self):
        assert isinstance(self.consumer.log, logging.Logger)
        assert self.consumer.log.name == 'baiocas.transports.util.MessageConsumer'

    def test_successful(self):
        messages = [
            Message(channel='/test', id='1'),
            Message(channel='/test', id='2', data='dummy')
        ]
        for segment in Message.to_json(messages).partition('{'):
            self.consumer.dataReceived(segment)
        self.consumer.connectionLost(Failure(exc_value=ResponseDone()))
        assert self.deferred.called
        assert self.deferred.result == messages

    def test_data_loss(self):
        messages = [Message(channel='/test', id='1', data='dummy')]
        for segment in Message.to_json(messages).partition('{'):
            self.consumer.dataReceived(segment)
        self.consumer.connectionLost(Failure(exc_value=PotentialDataLoss()))
        assert self.deferred.called
        assert self.deferred.result == messages

    def test_buffer_overflow(self):
        messages = [Message(channel='/test', id='1', data='')]
        data = Message.to_json(messages)
        with patch.object(MessageConsumer, 'MAXIMUM_SIZE', new=len(data)):
            consumer = MessageConsumer(self.deferred)
            consumer.dataReceived(data + 'x')
            consumer.dataReceived('x')
        consumer.connectionLost(Failure(exc_value=ResponseDone()))
        assert self.deferred.called
        assert self.deferred.result == messages

    def test_failure(self):
        messages = [Message(channel='/test', id='1', data='dummy')]
        for segment in Message.to_json(messages).partition('{'):
            self.consumer.dataReceived(segment)
        failure = Failure(exc_value=Error(NOT_FOUND))
        self.consumer.connectionLost(failure)
        assert self.deferred.called
        assert isinstance(self.deferred.result.value, errors.CommunicationError)
        assert self.deferred.result.value.transport_exception == failure
