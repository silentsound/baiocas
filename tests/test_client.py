from mock import Mock, patch
from twisted.trial.unittest import TestCase
import logging

from baiocas import errors
from baiocas.channel_id import ChannelId
from baiocas.client import Client
from baiocas.extensions.base import Extension
from baiocas.status import ClientStatus
from baiocas.message import Message
from baiocas.transports.base import Transport


class MockExtension(Extension):

    def __init__(self, name, raise_exception=False):
        super(MockExtension, self).__init__()
        self.__name = name
        self.__raise_exception = raise_exception
        self.received_messages = []
        self.sent_messages = []

    def clear_messages(self):
        self.received_messages = []
        self.sent_messages = []

    def receive(self, message):
        self.received_messages.append(message)
        message.setdefault('__receive_extensions__', []).append(self.__name)
        if self.__raise_exception:
            raise Exception()
        return message

    def send(self, message):
        self.sent_messages.append(message)
        message.setdefault('__send_extensions__', []).append(self.__name)
        if self.__raise_exception:
            raise Exception()
        return message


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
        self.sent_messages += messages


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

    def connect_client(self, client_id='client-1'):
        self.client.handshake()
        self.transport.receive([
            Message(
                channel=ChannelId.META_HANDSHAKE,
                successful=True,
                client_id=client_id,
                supported_connection_types=[self.transport.name],
                version=Client.BAYEUX_VERSION
            )
        ])
        self.transport.receive([
            Message(
                channel=ChannelId.META_CONNECT,
                successful=True
            )
        ])
        self.transport.clear_sent_messages()

    def create_mock_function(self, name='mock', **kwargs):
        mock = Mock(**kwargs)
        mock.__name__ = name
        return mock

    def disconnect_client(self):
        self.client.disconnect()
        self.transport.receive([
            Message(
                channel=ChannelId.META_DISCONNECT,
                successful=True
            )
        ])
        self.transport.clear_sent_messages()

    def setUp(self):
        self.client = Client('http://www.example.com')
        self.transport = MockTransport('mock-transport')
        self.client.register_transport(self.transport)
        self.mock_message = Message(channel='/test', data='dummy')

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
        self.connect_client()
        assert not self.client.is_disconnected
        self.disconnect_client()
        assert self.client.is_disconnected

    def test_message_id(self):
        assert self.client.message_id == 0
        self.client.handshake()
        assert self.client.message_id == 1

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

    def test_get_channel(self):
        channel = self.client.get_channel('/test')
        assert channel.channel_id == '/test'
        assert self.client.get_channel('/test') is channel
        assert self.client.get_channel(ChannelId('/test')) is channel
        other_channel = self.client.get_channel('/Test')
        assert other_channel.channel_id == '/Test'
        assert channel is not other_channel

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

    def test_register_extension(self):

        # Register extensions
        mock_extension_1 = MockExtension('mock-extension-1')
        mock_extension_2 = MockExtension('mock-extension-2')
        assert self.client.register_extension(mock_extension_1)
        assert self.client.register_extension(mock_extension_2)
        assert mock_extension_1.client is self.client
        assert mock_extension_2.client is self.client

        # Check that they get called for received messages
        mock_messages = [self.mock_message.copy()]
        self.client.receive_messages(mock_messages)
        assert mock_extension_1.received_messages == mock_messages
        assert mock_extension_1.sent_messages == []
        assert mock_extension_2.received_messages == mock_messages
        assert mock_extension_2.sent_messages == []

        # Connect the client to test sending
        self.connect_client()
        mock_extension_1.clear_messages()
        mock_extension_2.clear_messages()

        # Check that they get called for sent messages
        mock_message = self.mock_message.copy()
        self.client.send(mock_message)
        assert mock_extension_1.received_messages == []
        assert mock_extension_1.sent_messages == [mock_message]
        assert mock_extension_2.received_messages == []
        assert mock_extension_2.sent_messages == [mock_message]

    def test_register_listener(self):

        # Test the basic functionality
        event = self.client.EVENT_EXTENSION_EXCEPTION
        mock_listener_1 = self.create_mock_function()
        listener_id = self.client.register_listener(event, mock_listener_1, 1, foo='bar')
        assert not mock_listener_1.called
        self.client.fire(event)
        mock_listener_1.assert_called_once_with(self.client, 1, foo='bar')
        mock_listener_1.reset_mock()

        # Make sure multiple listeners per event can be registered
        mock_listener_2 = self.create_mock_function()
        self.client.register_listener(event, mock_listener_2)
        self.client.fire(event)
        mock_listener_1.assert_called_once_with(self.client, 1, foo='bar')
        mock_listener_2.assert_called_once_with(self.client)

        # Make sure listeners are registered only for the right event
        self.client.fire('mock-event')
        assert mock_listener_1.call_count == 1
        assert mock_listener_2.call_count == 1

        # Make sure the right listener ID is returned
        assert self.client.unregister_listener(listener_id)
        self.client.fire(event)
        assert mock_listener_1.call_count == 1
        assert mock_listener_2.call_count == 2

    def test_register_transport(self):
        transport2 = MockTransport('mock-transport-2')
        assert not self.client.register_transport(self.transport)
        assert self.client.register_transport(transport2)
        assert transport2.name in self.client.get_known_transports()

    def test_unregister_extension(self):

        # Connect the client to test sending messages
        self.connect_client()

        # Create the extensions
        mock_extension_1 = MockExtension('mock-extension-1')
        mock_extension_2 = MockExtension('mock-extension-2')

        # Check that unregistering invalid extensions doesn't fail
        assert not self.client.unregister_extension(mock_extension_1)

        # Register the extensions
        assert self.client.register_extension(mock_extension_1)
        assert self.client.register_extension(mock_extension_2)
        assert mock_extension_1.client is self.client
        assert mock_extension_2.client is self.client

        # Unregister the extension
        assert self.client.unregister_extension(mock_extension_1)
        assert mock_extension_1.client is None
        assert mock_extension_2.client is self.client

        # Make sure messages only get routed to registered extensions
        mock_messages = [self.mock_message.copy()]
        self.client.receive_messages(mock_messages)
        assert mock_extension_1.received_messages == []
        assert mock_extension_1.sent_messages == []
        assert mock_extension_2.received_messages == mock_messages
        assert mock_extension_2.sent_messages == []
        self.client.send(mock_messages[0])
        assert mock_extension_1.received_messages == []
        assert mock_extension_1.sent_messages == []
        assert mock_extension_2.received_messages == mock_messages
        assert mock_extension_2.sent_messages == mock_messages

    def test_unregister_listener(self):

        # Add a listener
        event = self.client.EVENT_EXTENSION_EXCEPTION
        mock_listener = self.create_mock_function()
        listener_id = self.client.register_listener(event, mock_listener)

        # Check validation of optional arguments
        self.assertRaises(ValueError, self.client.unregister_listener)
        self.assertRaises(ValueError, self.client.unregister_listener, id=listener_id, event=event)
        self.assertRaises(ValueError, self.client.unregister_listener, id=listener_id, function=mock_listener)

        # Make sure non-matches are handled correctly
        assert not self.client.unregister_listener(id=listener_id - 1)
        assert not self.client.unregister_listener(event='mock-event')
        assert not self.client.unregister_listener(function=self.create_mock_function())
        assert not self.client.unregister_listener(event='mock-event', function=mock_listener)
        assert not self.client.unregister_listener(event=event, function=self.create_mock_function())

        # Test removal by ID
        assert self.client.unregister_listener(id=listener_id)
        self.client.fire(event)
        assert not mock_listener.called

        # Test removal by event
        self.client.register_listener(event, mock_listener)
        self.client.register_listener(event, mock_listener)
        self.client.register_listener('mock-event', mock_listener)
        self.client.fire(event)
        assert mock_listener.call_count == 2
        assert self.client.unregister_listener(event=event)
        self.client.fire(event)
        assert mock_listener.call_count == 2
        self.client.fire('mock-event')
        assert mock_listener.call_count == 3
        mock_listener.reset_mock()

        # Test removal by function
        mock_listener_2 = self.create_mock_function()
        self.client.register_listener(event, mock_listener)
        self.client.register_listener(event, mock_listener_2)
        self.client.register_listener(event, mock_listener)
        self.client.fire(event)
        assert mock_listener.call_count == 2
        assert mock_listener_2.call_count == 1
        assert self.client.unregister_listener(function=mock_listener)
        self.client.fire(event)
        assert mock_listener.call_count == 2
        assert mock_listener_2.call_count == 2
        mock_listener.reset_mock()
        mock_listener_2.reset_mock()

        # Test removal by event and function
        self.client.register_listener(event, mock_listener)
        self.client.register_listener(event, mock_listener)
        self.client.register_listener('mock-event', mock_listener)
        self.client.fire(event)
        assert mock_listener.call_count == 2
        assert mock_listener_2.call_count == 1
        assert self.client.unregister_listener(event=event, function=mock_listener)
        self.client.fire(event)
        assert mock_listener.call_count == 2
        assert mock_listener_2.call_count == 2
        self.client.fire('mock-event')
        assert mock_listener.call_count == 3

    def test_unregister_transport(self):
        assert len(self.client.get_known_transports()) == 1
        assert self.client.unregister_transport('bad-transport') is None
        assert self.client.unregister_transport(self.transport.name.upper()) is None
        assert self.client.unregister_transport(self.transport.name) is self.transport
        assert self.client.unregister_transport(self.transport.name) is None
        assert len(self.client.get_known_transports()) == 0

    def test_batch(self):
        self.connect_client()
        mock_message = self.mock_message.copy()
        with self.client.batch():
            assert self.client.is_batching
            self.client.send(mock_message)
            assert self.transport.sent_messages == []
        assert not self.client.is_batching
        assert self.transport.sent_messages == [mock_message]
