from mock import Mock
from unittest import TestCase

from baiocas.channel import Channel
from baiocas.channel_id import ChannelId
from baiocas.client import Client
from baiocas.listener import Listener
from baiocas.message import Message


class TestChannel(TestCase):

    def setUp(self):
        self.client = Mock(spec_set=Client)
        self.channel_id = ChannelId('/test')
        self.channel = Channel(self.client, self.channel_id)
        self.mock_message = Message(data='dummy')

    def create_mock_function(self, name='mock', **kwargs):
        mock = Mock(**kwargs)
        mock.__name__ = name
        return mock

    def test_repr(self):
        assert repr(self.channel) == self.channel_id

    def test_channel_id(self):
        assert self.channel.channel_id is self.channel_id

    def test_is_meta(self):
        assert not self.channel.is_meta
        channel = Channel(self.client, ChannelId.META_HANDSHAKE)
        assert channel.is_meta

    def test_is_wild(self):
        assert not self.channel.is_wild
        channel = Channel(self.client, '/test/*')
        assert channel.is_wild
        channel = Channel(self.client, '/*')
        assert channel.is_wild
        channel = Channel(self.client, '/test/**')
        assert not channel.is_wild
        channel = Channel(self.client, '*')
        assert not channel.is_wild

    def test_is_wild_deep(self):
        assert not self.channel.is_wild_deep
        channel = Channel(self.client, '/test/**')
        assert channel.is_wild_deep
        channel = Channel(self.client, '/**')
        assert channel.is_wild_deep
        channel = Channel(self.client, '/*')
        assert not channel.is_wild_deep
        channel = Channel(self.client, '**')
        assert not channel.is_wild_deep

    def test_parts(self):
        assert self.channel.parts == ['test']
        channel = Channel(self.client, '/test/some/channel')
        assert channel.parts == ['test', 'some', 'channel']
        channel = Channel(self.client, '')
        assert channel.parts == []

    def test_has_subscriptions(self):
        assert not self.channel.has_subscriptions
        mock_listener = self.create_mock_function()
        self.channel.add_listener(mock_listener)
        assert not self.channel.has_subscriptions
        mock_subscription = self.create_mock_function()
        self.channel.subscribe(mock_subscription)
        assert self.channel.has_subscriptions
        assert self.channel.remove_listener(function=mock_listener)
        assert self.channel.has_subscriptions
        assert self.channel.unsubscribe(function=mock_subscription)
        assert not self.channel.has_subscriptions

    def test_add_listener(self):
        mock_listener = self.create_mock_function()
        listener_id = self.channel.add_listener(mock_listener, 1, foo='bar')
        assert not mock_listener.called
        self.channel.notify_listeners(self.channel, self.mock_message)
        mock_listener.assert_called_once_with(self.channel, self.mock_message, 1, foo='bar')
        assert self.channel.remove_listener(id=listener_id)

    def test_clear_listeners(self):
        self.channel.clear_listeners()
        mock_listener = self.create_mock_function()
        mock_subscription = self.create_mock_function()
        listener_id = self.channel.add_listener(mock_listener)
        self.channel.subscribe(mock_subscription)
        self.channel.clear_listeners()
        assert not self.channel.remove_listener(id=listener_id)
        self.channel.notify_listeners(self.channel, self.mock_message)
        assert not mock_listener.called
        mock_subscription.assert_called_once_with(self.channel, self.mock_message)

    def test_clear_subscriptions(self):
        self.channel.clear_subscriptions()
        mock_listener = self.create_mock_function()
        mock_subscription = self.create_mock_function()
        self.channel.add_listener(mock_listener)
        subscription_id = self.channel.subscribe(mock_subscription)
        self.channel.clear_subscriptions()
        assert not self.channel.unsubscribe(id=subscription_id)
        self.channel.notify_listeners(self.channel, self.mock_message)
        mock_listener.assert_called_once_with(self.channel, self.mock_message)
        assert not mock_subscription.called

    def test_get_wilds(self):
        channel = Channel(self.client, '/test/some/channel')
        assert channel.get_wilds() == [
            '/test/some/*',
            '/test/some/**',
            '/test/**',
            '/**'
        ]
        channel = Channel(self.client, '/')
        assert channel.get_wilds() == [
            '/*',
            '/**'
        ]
        channel = Channel(self.client, '')
        assert channel.get_wilds() == []

    def test_notify_listeners(self):
        mock_listener = self.create_mock_function()
        mock_subscription_1 = self.create_mock_function()
        mock_subscription_2 = self.create_mock_function(side_effect=Exception())
        mock_subscription_3 = self.create_mock_function()
        self.channel.add_listener(mock_listener, 1, foo='bar1')
        self.channel.subscribe(mock_subscription_1, 2, foo='bar2')
        subscription_id = self.channel.subscribe(mock_subscription_2, 3)
        self.channel.subscribe(mock_subscription_3, foo='bar4')
        self.channel.notify_listeners(self.channel, self.mock_message)
        mock_listener.assert_called_once_with(self.channel, self.mock_message, 1, foo='bar1')
        mock_subscription_1.assert_called_once_with(self.channel, self.mock_message, 2, foo='bar2')
        mock_subscription_2.assert_called_once_with(self.channel, self.mock_message, 3)
        mock_subscription_3.assert_called_once_with(self.channel, self.mock_message, foo='bar4')
        self.client.fire.assert_called_once_with(
            self.client.EVENT_LISTENER_EXCEPTION,
            Listener(
                id=subscription_id,
                function=mock_subscription_2,
                extra_args=(3,),
                extra_kwargs={}
            ),
            self.mock_message,
            mock_subscription_2.side_effect
        )

    def test_notify_listeners_without_data(self):
        mock_listener = self.create_mock_function()
        mock_subscription = self.create_mock_function()
        self.mock_message.data = None
        self.channel.add_listener(mock_listener)
        self.channel.subscribe(mock_subscription)
        self.channel.notify_listeners(self.channel, self.mock_message)
        mock_listener.assert_called_once_with(self.channel, self.mock_message)
        assert not mock_subscription.called

    def test_notify_listeners_with_other_channel(self):
        mock_listener = self.create_mock_function()
        mock_subscription = self.create_mock_function()
        other_channel = Channel(self.client, '/other')
        self.channel.add_listener(mock_listener)
        self.channel.subscribe(mock_subscription)
        self.channel.notify_listeners(other_channel, self.mock_message)
        mock_listener.assert_called_once_with(other_channel, self.mock_message)
        mock_subscription.assert_called_once_with(other_channel, self.mock_message)

    def test_publish(self):
        self.channel.publish('dummy')
        self.client.send.assert_called_once_with({
            'channel': '/test',
            'data': 'dummy'
        })
        self.channel.publish('dummy', properties={'id': '1'})
        self.client.send.assert_called_with({
            'channel': '/test',
            'data': 'dummy',
            'id': '1'
        })

    def test_remove_listener(self):

        # Add a listener
        mock_listener = self.create_mock_function()
        listener_id = self.channel.add_listener(mock_listener)

        # Check validation of optional arguments
        self.assertRaises(ValueError, self.channel.remove_listener)
        self.assertRaises(ValueError, self.channel.remove_listener, id=listener_id, function=mock_listener)

        # Make sure non-matches are handled correctly
        assert not self.channel.remove_listener(id=listener_id - 1)
        assert not self.channel.remove_listener(function=self.create_mock_function())

        # Test removal by ID
        assert self.channel.remove_listener(id=listener_id)
        self.channel.notify_listeners(self.channel, self.mock_message)
        assert not mock_listener.called

        # Test removal by function
        mock_listener_2 = self.create_mock_function()
        self.channel.add_listener(mock_listener)
        self.channel.add_listener(mock_listener_2)
        self.channel.add_listener(mock_listener)
        self.channel.notify_listeners(self.channel, self.mock_message)
        assert mock_listener.call_count == 2
        assert mock_listener_2.call_count == 1
        assert self.channel.remove_listener(function=mock_listener)
        self.channel.notify_listeners(self.channel, self.mock_message)
        assert mock_listener.call_count == 2
        assert mock_listener_2.call_count == 2

    def test_subscribe(self):
        mock_subscription = self.create_mock_function()
        subscription_id = self.channel.subscribe(mock_subscription, 1, foo='bar')
        self.client.send.assert_called_once_with({
            'channel': ChannelId.META_SUBSCRIBE,
            'subscription': self.channel_id
        })
        self.channel.subscribe(mock_subscription)
        assert self.client.send.call_count == 1
        self.channel.notify_listeners(self.channel, self.mock_message)
        assert mock_subscription.call_args_list == [
            ((self.channel, self.mock_message, 1), {'foo': 'bar'}),
            ((self.channel, self.mock_message),)
        ]
        assert self.channel.unsubscribe(id=subscription_id)
        assert self.channel.unsubscribe(function=mock_subscription)

    def test_subscribe_with_properties(self):
        mock_subscription = self.create_mock_function()
        self.channel.subscribe(mock_subscription, 1, foo='bar', properties={'id': '1'})
        self.client.send.assert_called_once_with({
            'channel': ChannelId.META_SUBSCRIBE,
            'subscription': self.channel_id,
            'id': '1'
        })
        self.channel.notify_listeners(self.channel, self.mock_message)
        mock_subscription.assert_called_once_with(self.channel, self.mock_message, 1, foo='bar')

    def test_unsubscribe(self):
        mock_subscription = self.create_mock_function()
        subscription_id = self.channel.subscribe(mock_subscription)
        self.client.send.reset_mock()
        self.assertRaises(ValueError, self.channel.unsubscribe)
        self.assertRaises(ValueError, self.channel.unsubscribe, id=subscription_id, function=mock_subscription)
        assert not self.channel.unsubscribe(id=subscription_id - 1)
        assert not self.channel.unsubscribe(function=self.create_mock_function())
        assert self.channel.unsubscribe(id=subscription_id)
        self.client.send.assert_called_once_with({
            'channel': ChannelId.META_UNSUBSCRIBE,
            'subscription': self.channel_id
        })
        self.channel.notify_listeners(self.channel, self.mock_message)
        assert not mock_subscription.called
        self.channel.subscribe(mock_subscription)
        self.channel.subscribe(mock_subscription)
        self.client.send.reset_mock()
        self.channel.notify_listeners(self.channel, self.mock_message)
        assert mock_subscription.call_count == 2
        assert self.channel.unsubscribe(function=mock_subscription)
        assert self.client.send.call_count == 1
        self.channel.notify_listeners(self.channel, self.mock_message)
        assert mock_subscription.call_count == 2

    def test_unsubscribe_with_properties(self):
        mock_subscription = self.create_mock_function()
        self.channel.subscribe(mock_subscription)
        self.client.send.reset_mock()
        assert self.channel.unsubscribe(function=mock_subscription, properties={'id': '1'})
        self.client.send.assert_called_once_with({
            'channel': ChannelId.META_UNSUBSCRIBE,
            'subscription': self.channel_id,
            'id': '1'
        })
        self.channel.notify_listeners(self.channel, self.mock_message)
        assert not mock_subscription.called
