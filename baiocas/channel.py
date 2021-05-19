import logging

from baiocas.channel_id import ChannelId
from baiocas.listener import Listener
from baiocas.message import Message


class Channel(object):

    def __init__(self, client, channel_id):
        self.log = logging.getLogger('%s.%s' % (self.__module__, self.__class__.__name__))
        self._client = client
        self._channel_id = ChannelId.convert(channel_id)
        self._listener_id = 0
        self._listeners = []
        self._subscriptions = []

    def __repr__(self):
        return self._channel_id

    @property
    def channel_id(self):
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

    def _add_listener(self, listeners, function, extra_args, extra_kwargs):
        self._listener_id += 1
        listeners.append(Listener(
            id=self._listener_id,
            function=function,
            extra_args=extra_args,
            extra_kwargs=extra_kwargs
        ))
        self.log.debug('Added listener "%s" for channel %s' %
                       (function.__name__, self._channel_id))
        return self._listener_id

    def _notify_listeners(self, listeners, channel, message):
        for listener in listeners:
            try:
                self.log.debug('Notifying listener "%s" of message' % listener.function.__name__)
                listener.function(channel, message, *listener.extra_args, **listener.extra_kwargs)
            except Exception as ex:
                self.log.warn('Exception with listener "%s" with %s: %s' %
                              (listener.function.__name__, message, ex))
                self._client.fire(self._client.EVENT_LISTENER_EXCEPTION, listener, message, ex)

    def _remove_listener(self, listeners, id=None, function=None):
        if (id is not None) == (function is not None):
            raise ValueError('Either id or function must be given')
        success = False
        if id is not None:
            for index, listener in enumerate(listeners):
                if listener.id == id:
                    function = listener.function
                    del listeners[index]
                    success = True
                    break
        else:
            to_remove = []
            for index, listener in enumerate(listeners):
                if function == listener.function:
                    to_remove.append(index)
            for index in reversed(to_remove):
                del listeners[index]
            success = bool(to_remove)
        if success:
            self.log.debug('Removed listener(s) "%s" for channel %s' %
                           (function.__name__, self._channel_id))
        return success

    def add_listener(self, function, *extra_args, **extra_kwargs):
        return self._add_listener(self._listeners, function, extra_args, extra_kwargs)

    def clear_listeners(self):
        self._listeners = []
        self.log.debug('Cleared listeners for channel %s' % self._channel_id)

    def clear_subscriptions(self):
        self._subscriptions = []
        self.log.debug('Cleared subscriptions for channel %s' % self._channel_id)

    def get_wilds(self):
        return self._channel_id.get_wilds()

    def notify_listeners(self, channel, message):
        self._notify_listeners(self._listeners, channel, message)
        if message.data:
            self._notify_listeners(self._subscriptions, channel, message)

    def publish(self, data, properties=None):
        self.log.debug('Publishing data to channel: %s' % data)
        message = Message(properties, channel=self._channel_id, data=data)
        self._client.send(message)

    def remove_listener(self, id=None, function=None):
        return self._remove_listener(self._listeners, id=id, function=function)

    def subscribe(self, function, *extra_args, **extra_kwargs):
        properties = None
        if 'properties' in extra_kwargs:
            properties = extra_kwargs.pop('properties')
        if not self.has_subscriptions:
            self.log.debug('Subscribe to channel "%s"' % self._channel_id)
            message = Message(properties,
                              channel=ChannelId.META_SUBSCRIBE,
                              subscription=self._channel_id
                              )
            self._client.send(message)
        return self._add_listener(self._subscriptions, function, extra_args, extra_kwargs)

    def unsubscribe(self, id=None, function=None, properties=None):
        success = self._remove_listener(self._subscriptions, id=id, function=function)
        if not self.has_subscriptions:
            self.log.debug('Channel has no remaining subscriptions, sending unsubscribe')
            message = Message(properties,
                              channel=ChannelId.META_UNSUBSCRIBE,
                              subscription=self._channel_id
                              )
            self._client.send(message)
        return success
