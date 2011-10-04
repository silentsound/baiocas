import logging

from channel_id import ChannelId
from message import Message


class Channel(object):

    def __init__(self, client, channel_id):
        self.log = logging.getLogger('%s.%s' % (self.__module__, self.__class__.__name__))
        self._client = client
        self._channel_id = channel_id
        self._listeners = []
        self._subscriptions = []

    def __repr__(self):
        return self._channel_id

    @property
    def is_meta(self):
        return self._channel_id.is_meta

    @property
    def is_wild(self):
        return self._channel_id.is_wild

    @property
    def is_wild_deep(self):
        return self._channel_id.is_wild_deep

    @property
    def parts(self):
        return self._channel_id.parts

    @property
    def has_subscriptions(self):
        return len(self._subscriptions) > 0

    def add_listener(self, listener):
        self._listeners.append(listener)
        self.log.debug('Added listener %s for channel %s' % (listener, self._channel_id))

    def clear_listeners(self):
        self._listeners = []

    def clear_subscriptions(self):
        self._subscriptions = []
        self.log.debug('Cleared subscriptions for channel %s' % self.channel_id)

    def get_wilds(self):
        return self._channel_id.get_wilds()

    def notify_listeners(self, message):
        for listener in self._listeners:
            try:
                self.log.debug('Notifying listener %s of message' % listener)
                listener(self, message)
            except Exception, ex:
                self.log.debug('Exception during notification of %s with %s: %s' % \
                    (listener, message, ex))
                self._client.fire(self._client.EVENT_LISTENER_EXCEPTION, listener, message, ex)

    def publish(self, content, properties=None):
        self.log.debug('Publishing content to channel: %s' % content)
        message = Message(properties, channel=self._channel_id, data=content)
        self._client.send(message)

    def remove_listener(self, listener):
        if listener in self._listeners:
            self._listeners.remove(listener)
            self.log.debug('Removed listener %s for channel %s' % (listener, self._channel_id))

    def subscribe(self, listener, properties=None):
        self.log.debug('Subscribing listener %s to channel' % listener)
        if not self.has_subscriptions:
            self.log.debug('Channel has no existing subscriptions, sending subscribe')
            message = Message(properties,
                channel=ChannelId.META_SUBSCRIBE,
                subscription=self._channel_id
            )
            self._client.send(message)
        self._subscriptions.append(listener)

    def unsubscribe(self, listener):
        self.log.debug('Unsubscribing listener %s from channel' % listener)
        if listener in self._listeners:
            self._listeners.remove(listener)
        if self.has_subscriptions:
            return
        self.log.debug('Channel has no remaining subscriptions, sending unsubscribe')
        message = Message(properties,
            channel=ChannelId.META_UNSUBSCRIBE,
            subscription=self._channel_id
        )
        self._client.send(message)
