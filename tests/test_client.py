from mock import Mock, patch
from twisted.trial.unittest import TestCase
import logging

from baiocas import errors
from baiocas.channel_id import ChannelId
from baiocas.client import Client
from baiocas.status import ClientStatus
from baiocas.message import Message
from baiocas.transports.base import Transport


class MockTransport(Transport):

    def __init__(self, name, only_versions=None):
        self.__name = name
        self.__only_versions = only_versions
        self.sent_messages = []
        super(MockTransport, self).__init__()

    @property
    def name(self):
        return self.__name

    def accept(self, bayeux_version):
        if self.__only_versions is None:
            return True
        return version in self.__only_versions

    def clear_sent_messages(self):
        self.sent_messages = []

    def receive(self, messages):
        for message in messages:
            print 'Receive: %s' % message
        self._client.receive_messages(messages)

    def send(self, messages):
        for message in messages:
            print 'Send: %s' % message
        self.sent_messages.append(messages)


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

    def create_mock_function(self, name='mock', **kwargs):
        mock = Mock(**kwargs)
        mock.__name__ = name
        return mock

    def setUp(self):
        self.client = Client('http://www.example.com')
        self.transport = MockTransport('mock-transport')
        self.client.register_transport(self.transport)
        self.mock_message = Message(data='dummy')

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
        assert not self.client.is_disconnected
        self.client.handshake()
        self.transport.receive([
            Message(
                channel=ChannelId.META_HANDSHAKE,
                id='1',
                successful=True,
                client_id='client-1',
                supported_connection_types=[self.transport.name],
                version=Client.BAYEUX_VERSION
            )
        ])
        self.transport.receive([
            Message(
                channel=ChannelId.META_CONNECT,
                id='2',
                successful=True
            )
        ])
        assert not self.client.is_disconnected
        self.client.disconnect()
        self.transport.receive([
            Message(
                channel=ChannelId.META_DISCONNECT,
                id='3',
                successful=True
            )
        ])
        assert self.client.is_disconnected

    def test_options(self):
        options = self.client.options
        assert options == self.DEFAULT_OPTIONS
        options['temp'] = 'dummy'
        assert self.client.options == self.DEFAULT_OPTIONS

    def test_clear_subscriptions(self):
        mock_listener = self.create_mock_function()
        mock_subscription = self.create_mock_function()
        channel_1 = self.client.get_channel('/test1')
        channel_2 = self.client.get_channel('/test2')
        channel_1.add_listener(mock_listener)
        channel_1.subscribe(mock_subscription)
        channel_1.subscribe(mock_subscription)
        channel_2.subscribe(mock_subscription)
        assert channel_1.has_subscriptions
        assert channel_2.has_subscriptions
        self.client.clear_subscriptions()
        assert not channel_1.has_subscriptions
        assert not channel_2.has_subscriptions
        channel_1.notify_listeners(self.mock_message)
        channel_2.notify_listeners(self.mock_message)
        mock_listener.called_with(channel_1, self.mock_message)
        assert not mock_subscription.called

    def test_configure(self):
        
        # Make sure blank calls keep the defaults
        self.client.configure()
        assert self.client.options == self.DEFAULT_OPTIONS

        # Make sure we can add an option
        self.client.configure(temp='dummy')
        options = self.DEFAULT_OPTIONS.copy()
        options['temp'] = 'dummy'
        assert self.client.options == options

        # Check that the option sticks
        self.client.configure()
        assert self.client.options == options

        # Make sure we can change existing options
        self.client.configure(temp=False)
        options['temp'] = False
        assert self.client.options == options

        # Make sure we can change a default
        self.client.configure(backoff_period_increment=0)
        options['backoff_period_increment'] = 0
        assert self.client.options == options

    def test_end_batch(self):
        self.assertRaises(errors.BatchError, self.client.end_batch)
        with patch.object(self.client, 'flush_batch') as mock_flush_batch:
            self.client.start_batch()
            self.client.start_batch()
            self.client.end_batch()
            assert not mock_flush_batch.called
            self.client.end_batch()
            assert mock_flush_batch.call_count == 1
        self.assertRaises(errors.BatchError, self.client.end_batch)

    def test_fire(self):

        # Register mock listeners
        event = self.client.EVENT_EXTENSION_EXCEPTION
        mock_listener = self.create_mock_function()
        bad_listener = self.create_mock_function(side_effect=Exception())
        self.client.register_listener(event, mock_listener)
        self.client.register_listener(event, bad_listener)
        self.client.register_listener(event, mock_listener, 2, foo='bar2')
        self.client.register_listener(event, mock_listener, 3)
        self.client.register_listener(event, mock_listener, foo='bar4')

        # Make sure the listeners don't fire for a different event
        self.client.fire('mock_event')
        assert not mock_listener.called

        # Check the basic functionality
        self.client.fire(event)
        assert mock_listener.call_args_list == [
            ((self.client,),),
            ((self.client, 2,), {'foo': 'bar2'}),
            ((self.client, 3,),),
            ((self.client,), {'foo': 'bar4'})
        ]
        assert bad_listener.call_count == 1
        mock_listener.reset_mock()

        # Make sure args/kwargs get combined correctly
        self.client.fire(event, 5, 6, temp='dummy', foo='bar5')
        assert mock_listener.call_args_list == [
            ((self.client, 5, 6), {'temp': 'dummy', 'foo': 'bar5'}),
            ((self.client, 5, 6, 2,), {'temp': 'dummy', 'foo': 'bar2'}),
            ((self.client, 5, 6, 3,), {'temp': 'dummy', 'foo': 'bar5'}),
            ((self.client, 5, 6), {'temp': 'dummy', 'foo': 'bar4'})
        ]

    def test_get_known_transports(self):
        transports = self.client.get_known_transports()
        assert len(transports) == 1
        assert self.transport.name in transports
        transport2 = MockTransport('mock-transport-2', only_versions=[])
        self.client.register_transport(transport2)
        transports = self.client.get_known_transports()
        assert len(transports) == 2
        assert self.transport.name in transports
        assert transport2.name in transports

    def test_get_transport(self):
        assert self.client.get_transport(self.transport.name) is self.transport
        assert self.client.get_transport('bad-transport') is None
        assert self.client.get_transport(self.transport.name.upper()) is None
