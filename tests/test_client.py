from unittest import TestCase
import logging

from baiocas.channel_id import ChannelId
from baiocas.client import Client
from baiocas.status import ClientStatus
from baiocas.transports.base import Transport


class MockTransport(Transport):

    @property
    def name(self):
        return 'mock-transport'

    def accept(self, bayeux_version):
        return True

    def send(self, messages):
        pass


class TestClient(TestCase):

    DEFAULT_OPTIONS = {
        'backoff_period_increment': 1000,
        'maximum_backoff_period': 60000,
        'reverse_incoming_extensions': True,
        'advice': {
            'timeout': 60000,
            'interval': 0,
            'reconnect': 'retry'
        }
    }

    def setUp(self):
        self.client = Client('http://www.example.com')
        self.transport = MockTransport()
        self.client.register_transport(self.transport)

    def test_init(self):
        assert isinstance(self.client.log, logging.Logger)
        assert self.client.log.name == 'baiocas.client.Client'
        assert self.client.advice == {}
        assert self.client.backoff_period == 0
        assert self.client.client_id is None
        assert not self.client.is_batching
        assert not self.client.is_disconnected
        assert self.client.options == self.DEFAULT_OPTIONS
        assert self.client.status == ClientStatus.UNCONNECTED
        assert self.client.transport is None
        assert self.client.url == 'http://www.example.com'

    def test_advice(self):
        advice = self.client.advice
        assert advice == {}
        advice['temp'] = 'dummy'
        assert self.client.advice == {}

    def test_is_batching(self):
        assert not self.client.is_batching
        with self.client.batch():
            assert self.client.is_batching
        assert not self.client.is_batching

    def test_is_batching_manual(self):
        assert not self.client.is_batching
        self.client.start_batch()
        assert self.client.is_batching
        self.client.end_batch()
        assert not self.client.is_batching

    def test_is_batching_nested(self):
        assert not self.client.is_batching
        with self.client.batch():
            with self.client.batch():
                assert self.client.is_batching
            assert self.client.is_batching
        assert not self.client.is_batching

    def test_is_disconnected(self):
        self.client.handshake()

    def test_options(self):
        options = self.client.options
        assert options == self.DEFAULT_OPTIONS
        options['temp'] = 'dummy'
        assert self.client.options == self.DEFAULT_OPTIONS
