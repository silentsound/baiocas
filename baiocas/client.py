import logging
from contextlib import contextmanager
from datetime import timedelta

from tornado.ioloop import IOLoop

from baiocas import errors
from baiocas.channel import Channel
from baiocas.channel_id import ChannelId
from baiocas.listener import Listener
from baiocas.message import FailureMessage
from baiocas.message import Message
from baiocas.status import ClientStatus
from baiocas.transports.long_polling import LongPollingHttpTransport
from baiocas.transports.registry import TransportRegistry


class Client(object):

    BAYEUX_VERSION = '1.0'

    DEFAULT_OPTIONS = {
        'backoff_period_increment': 1000,
        'maximum_backoff_period': 60000,
        'reverse_incoming_extensions': True,
        'advice': {
            Message.FIELD_TIMEOUT: 60000,
            Message.FIELD_INTERVAL: 0,
            Message.FIELD_RECONNECT: Message.RECONNECT_RETRY
        }
    }

    EVENT_EXTENSION_EXCEPTION = 'extension_exception'

    EVENT_LISTENER_EXCEPTION = 'listener_exception'

    MINIMUM_BAYEUX_VERSION = '0.9'

    def __init__(self, url, io_loop=None, **options):

        # Set up a logger for the client
        self.log = logging.getLogger('%s.%s' % (self.__module__, self.__class__.__name__))

        # Save the URL
        self._url = url

        # Use the default IO loop if not provided
        self.io_loop = io_loop or IOLoop.instance()

        # Current client status and connection properties
        self._status = ClientStatus.UNCONNECTED
        self._connected = False
        self._scheduled_send = None
        self._backoff_period = 0
        self._advice = {}

        # Channels keyed by channel ID
        self._channels = {}

        # Active connection properties
        self._client_id = None
        self._message_id = 0

        # Transport registry and current transport
        self._transports = TransportRegistry()
        self._transport = None

        # Keep track of batches, both manual and internal
        self._batch_id = 0
        self._internal_batch = False
        self._message_queue = []

        # Extensions
        self._extensions = []

        # Event listeners keyed by event
        self._event_listener_id = 0
        self._event_listeners = {}

        # Configure the client
        self._options = self.DEFAULT_OPTIONS.copy()
        self.configure(**options)

    @property
    def advice(self):
        return self._advice.copy()

    @property
    def backoff_period(self):
        return self._backoff_period

    @property
    def client_id(self):
        return self._client_id

    @property
    def is_batching(self):
        return self._batch_id > 0 or self._internal_batch

    @property
    def is_disconnected(self):
        return ClientStatus.is_disconnected(self._status)

    @property
    def message_id(self):
        return self._message_id

    @property
    def options(self):
        return self._options.copy()

    @property
    def status(self):
        return self._status

    @property
    def transport(self):
        return self._transport

    @property
    def url(self):
        return self._url

    def _apply_extension(self, extension, message, outgoing=False):
        try:
            self.log.debug('Applying extension %s to message' % extension)
            method = outgoing and 'send' or 'receive'
            return getattr(extension, method)(message)
        except Exception as ex:
            self.log.warn('Exception during execution of extension %s: %s' %
                          (extension, ex))
            self.fire(self.EVENT_EXTENSION_EXCEPTION, message, ex, outgoing=outgoing)

    def _apply_incoming_extensions(self, message):
        self.log.debug('Applying extensions to incoming message')
        extensions = self._extensions
        if self._options['reverse_incoming_extensions']:
            self.log.debug('Reversing order of extensions')
            extensions = reversed(self._extensions)
        for extension in extensions:
            message = self._apply_extension(extension, message)
            if not message:
                self.log.debug('Message cancelled, skipping other extensions')
                break
        return message

    def _apply_outgoing_extensions(self, message):
        self.log.debug('Applying extensions to outgoing message')
        for extension in self._extensions:
            message = self._apply_extension(extension, message, outgoing=True)
            if not message:
                self.log.debug('Message cancelled, skipping other extensions')
                break
        return message

    def _cancel_delayed_send(self):
        if not self._scheduled_send:
            return
        if self._scheduled_send:
            self.log.debug('Cancelling delayed send')
            self.io_loop.remove_timeout(self._scheduled_send)
        self._scheduled_send = None

    def _connect(self):

        # Don't attempt to connect if we're disconnected. This doesn't make much
        # sense, but that's how the JavaScript client is implemented.
        if self.is_disconnected:
            self.log.debug('Client is disconnected, skipping connect')
            return

        # Create the message. In case of a reload or temporary loss of
        # connection, we want the next successful connect to return immediately
        # instead of being held by the server so that listeners can be notified
        # that the connection has been re-established.
        message = Message(
            channel=ChannelId.META_CONNECT,
            connection_type=self._transport.name
        )
        if not self._connected:
            message[Message.FIELD_ADVICE] = {
                Message.FIELD_TIMEOUT: 0
            }

        # Connect
        self._set_status(ClientStatus.CONNECTING)
        self.log.debug('Sending connect: %s' % message)
        self._send(message, for_setup=True)
        self._set_status(ClientStatus.CONNECTED)

    def _delay_connect(self):
        self.log.debug('Scheduling delayed connect')
        self._set_status(ClientStatus.CONNECTING)
        self._delay_send(self._connect)

    def _delay_handshake(self):
        self.log.debug('Scheduling delayed handshake')
        self._set_status(ClientStatus.HANDSHAKING)
        self._internal_batch = True
        self._delay_send(self._handshake, properties=self._handshake_properties)

    def _delay_send(self, method, *args, **kwargs):
        self._cancel_delayed_send()
        delay = self._advice['interval'] + self._backoff_period
        self.log.debug('Send scheduled in %sms, interval = %s, backoff = %s: %s' %
                       (delay, self._advice['interval'], self._backoff_period, method.__name__))
        if delay == 0:
            method(*args, **kwargs)
        else:
            self._scheduled_send = self.io_loop.add_timeout(
                timedelta(seconds=delay / 1000.0),
                lambda: method(*args, **kwargs)
            )

    def _disconnect(self, abort=False):
        if self._status == ClientStatus.DISCONNECTED:
            return
        self.log.debug('Disconnecting client')
        self._set_status(ClientStatus.DISCONNECTED)
        self._cancel_delayed_send()
        if abort:
            self.log.debug('Aborting transport')
            self._transport.abort()
        self._client_id = None
        self._batch_id = 0
        self._reset_backoff_period()
        if len(self._message_queue) > 0:
            self.log.debug('Failing queued messages')
            self._handle_failure(self._message_queue[:], errors.StatusError(self._status))
            self._message_queue = []

    def _get_next_message_id(self):
        self._message_id += 1
        return self._message_id

    def _handle_connect_failure(self, message, exception):
        self.log.debug('Handling failed connect')
        self._connected = False
        self._notify_connect_failure(FailureMessage.from_message(
            message,
            exception=exception,
            advice={
                FailureMessage.FIELD_RECONNECT: FailureMessage.RECONNECT_RETRY,
                FailureMessage.FIELD_INTERVAL: self._backoff_period,
            },
        ))

    def _handle_connect_response(self, message):
        self.log.debug('Handling connect response')
        if self.is_disconnected:
            self.log.debug('Client disconnected, discarding connect response')
            return
        self._connected = message.successful
        if self._connected:
            self.log.info('Client is now connected')
            self._notify_listeners(ChannelId.META_CONNECT, message)
            action = self._advice[Message.FIELD_RECONNECT]
            if action == Message.RECONNECT_RETRY:
                self._reset_backoff_period()
                self._delay_connect()
            elif action == Message.RECONNECT_NONE:
                self._disconnect()
            else:
                raise errors.ActionError(action)
        else:
            self.log.info('Client failed to connect')
            self._notify_connect_failure(message)

    def _handle_disconnect_failure(self, message, exception):
        self.log.debug('Handling failed disconnect')
        self._notify_disconnect_failure(FailureMessage.from_message(message, exception=exception))

    def _handle_disconnect_response(self, message):
        self.log.debug('Handling disconnect response')
        if message.successful:
            self.log.info('Client is now disconnected')
            self._disconnect()
            self._notify_listeners(ChannelId.META_DISCONNECT, message)
        else:
            self.log.info('Client failed to disconnect')
            self._notify_disconnect_failure(message)

    def _handle_failure(self, messages, exception):
        self.log.debug('Handling %d failed messages for exception: %s' % (len(messages), exception))
        for message in messages:
            handler = self._handle_message_failure
            if message.channel.is_meta:
                handler_name = '_handle_%s_failure' % '_'.join(message.channel.parts[1:])
                self.log.debug('Looking for handler named %s' % handler_name)
                if hasattr(self, handler_name):
                    handler = getattr(self, handler_name)
            self.log.debug('Passing message to handler %s' % handler.__name__)
            handler(message, exception)

    def _handle_handshake_failure(self, message, exception):
        self.log.debug('Handling failed handshake')
        self._notify_handshake_failure(FailureMessage.from_message(
            message,
            exception=exception,
            advice={
                FailureMessage.FIELD_RECONNECT: FailureMessage.RECONNECT_RETRY,
                FailureMessage.FIELD_INTERVAL: self._backoff_period,
            },
        ))

    def _handle_handshake_response(self, message):

        # Fail immediately if the message was not successful
        self.log.debug('Handling handshake response')
        if not message.successful:
            self.log.info('Client failed to handshake')
            self._notify_handshake_failure(message)
            return

        # Save the client ID
        self.log.info('Handshake successful, client ID = %s' % message.client_id)
        self._client_id = message.client_id

        # Negotiate a transport with the server
        new_transport = self._transports.negotiate_transport(
            message.supported_connection_types or [],
            message.version
        )
        if not new_transport:
            raise errors.TransportNegotiationError(
                self._transports.find_transports(message.version),
                message.supported_connection_types or []
            )
        elif self._transport != new_transport:
            self.log.debug('Transport %s -> %s' % (self._transport, new_transport))
            self._transport = new_transport

        # The new transport is now in place, so the listeners can perform a
        # publish() if they want. Notify the listeners of the connect below.
        self._notify_listeners(ChannelId.META_HANDSHAKE, message)

        # Handle the advice action
        action = self._advice[Message.FIELD_RECONNECT]
        if self.is_disconnected:
            action = Message.RECONNECT_NONE
        if action == Message.RECONNECT_RETRY:
            self._reset_backoff_period()
            self._delay_connect()
        elif action == Message.RECONNECT_NONE:
            self._disconnect()
        else:
            raise errors.ActionError(action)

        # End the internal batch and allow held messages from the application to
        # go to the server (see _handshake() where we start the internal batch).
        self._internal_batch = False
        self.flush_batch()

    def _handle_message_failure(self, message, exception):
        self.log.debug('Handling failed message')
        self._notify_message_failure(FailureMessage.from_message(message, exception=exception))

    def _handle_message_response(self, message):
        self.log.debug('Handling message response')
        if message.successful is None:
            self.log.debug('Client received message with blank successful flag')
            if message.data:
                self._notify_listeners(message.channel, message)
            else:
                self.log.warn('Unknown message received: %s' % message)
        elif message.successful is True:
            self.log.debug('Client received successful message')
            self._notify_listeners(ChannelId.META_PUBLISH, message)
        else:
            self.log.debug('Client received unsuccessful message')
            self._notify_message_failure(message)

    def _handle_subscribe_failure(self, message, exception):
        self.log.debug('Handling failed subscribe')
        self._notify_subscribe_failure(FailureMessage.from_message(message, exception=exception))

    def _handle_subscribe_response(self, message):
        self.log.debug('Handling subscribe response')
        channel = message.subscription
        if message.successful:
            self.log.info('Client subscribed to channel "%s"' % channel)
            self._notify_listeners(ChannelId.META_SUBSCRIBE, message)
        else:
            self.log.info('Client failed to subscribe to channel "%s"' % channel)
            self._notify_subscribe_failure(message)

    def _handle_unsubscribe_failure(self, message, exception):
        self.log.debug('Handling failed unsubscribe')
        self._notify_unsubscribe_failure(FailureMessage.from_message(message, exception=exception))

    def _handle_unsubscribe_response(self, message):
        self.log.debug('Handling unsubscribe response')
        channel = message.subscription
        if message.successful:
            self.log.info('Client unsubscribed from channel "%s"' % channel)
            self._notify_listeners(ChannelId.META_UNSUBSCRIBE, message)
        else:
            self.log.info('Client failed to unsubscribe from channel "%s"' % channel)
            self._notify_unsubscribe_failure(message)

    def _handshake(self, properties=None):

        # Reset state before starting
        self.log.info('Starting handshake')
        self._client_id = None
        self.clear_subscriptions()

        # Reset the transports if we're not retrying the handshake. If we are
        # retrying the handshake, either because another handshake failed and
        # we're backing off or because the server timed us out and asked us to
        # re-handshake, make sure that the next action is a connect if the
        # handshake succeeds.
        if self.is_disconnected:
            self.log.debug('Client disconnected, resetting advice')
            self._transports.reset()
            self._update_advice(self._options['advice'])
        else:
            self.log.debug('Client not disconnected, using retry advice')
            advice = self._advice.copy()
            advice[Message.FIELD_RECONNECT] = Message.RECONNECT_RETRY
            self._update_advice(advice)

        # Mark the start of an internal batch. Since all calls are asynchronous,
        # this ensures that no other messages are sent until the connection is
        # fully established.
        self._batch_id = 0
        self._internal_batch = True

        # Save the properties provided so we can reuse them during re-handshakes
        self._handshake_properties = properties

        # Figure out the tranpsorts to send to the server
        transport_names = self._transports.find_transports(self.BAYEUX_VERSION)
        self.log.debug('Supported transports: %s' % ', '.join(transport_names))

        # Create the handshake message
        message = Message(properties,
                          version=self.BAYEUX_VERSION,
                          minimum_version=self.MINIMUM_BAYEUX_VERSION,
                          channel=ChannelId.META_HANDSHAKE,
                          supported_connection_types=transport_names,
                          advice={
                              Message.FIELD_TIMEOUT: self._advice[Message.FIELD_TIMEOUT],
                              Message.FIELD_INTERVAL: self._advice[Message.FIELD_INTERVAL]
                          }
                          )

        # Pick the first available transport as the initial transport since we
        # don't know what the server currently supports
        self._transport = self._transports.negotiate_transport(
            transport_names,
            self.BAYEUX_VERSION
        )
        self.log.debug('Initial transport: %s' % self._transport)

        # Bypass the internal batch and send immediately
        self._set_status(ClientStatus.HANDSHAKING)
        self.log.debug('Sending handshake: %s' % message)
        self._send(message, for_setup=True)

    def _increase_backoff_period(self):
        if self._backoff_period < self._options['maximum_backoff_period']:
            self._backoff_period += self._options['backoff_period_increment']
            self.log.debug('Increasing backoff period to %s' % self._backoff_period)

    def _notify_connect_failure(self, message):
        self.log.debug('Notifying listeners of failed connect')
        self._notify_listeners(ChannelId.META_CONNECT, message)
        self._notify_listeners(ChannelId.META_UNSUCCESSFUL, message)
        action = self._advice[Message.FIELD_RECONNECT]
        if self.is_disconnected:
            action = Message.RECONNECT_NONE
        if action == Message.RECONNECT_RETRY:
            self.log.debug('Retry reconnect advice received')
            self._increase_backoff_period()
            self._delay_connect()
        elif action == Message.RECONNECT_HANDSHAKE:
            self.log.debug('Handshake reconnect advice received')
            self._transports.reset()
            self._reset_backoff_period()
            self._delay_handshake()
        elif action == Message.RECONNECT_NONE:
            self.log.debug('No reconnect advice received')
            self._disconnect()
        else:
            raise errors.ActionError(action)

    def _notify_disconnect_failure(self, message):
        self.log.debug('Notifying listeners of failed disconnect')
        self._disconnect(abort=True)
        self._notify_listeners(ChannelId.META_DISCONNECT, message)
        self._notify_listeners(ChannelId.META_UNSUCCESSFUL, message)

    def _notify_handshake_failure(self, message):
        self.log.debug('Notifying listeners of failed handshake')
        self._notify_listeners(ChannelId.META_HANDSHAKE, message)
        self._notify_listeners(ChannelId.META_UNSUCCESSFUL, message)
        if not self.is_disconnected and self._advice[Message.FIELD_RECONNECT] != Message.RECONNECT_NONE:
            self._increase_backoff_period()
            self._delay_handshake()
        else:
            self._disconnect()

    def _notify_listeners(self, channel_id, message):

        # Notify direct listeners
        self.log.debug('Notifying listeners for %s' % channel_id)
        channel = self.get_channel(channel_id)
        channel.notify_listeners(channel, message)

        # Notify the wildcard listeners
        for wild in channel.channel_id.get_wilds():
            self.log.debug('Notifying listeners for %s' % wild)
            wild_channel = self.get_channel(wild)
            wild_channel.notify_listeners(channel, message)

    def _notify_message_failure(self, message):
        self.log.debug('Notifying listeners of failed message')
        self._notify_listeners(ChannelId.META_PUBLISH, message)
        self._notify_listeners(ChannelId.META_UNSUCCESSFUL, message)

    def _notify_subscribe_failure(self, message):
        self.log.debug('Notifying listeners of failed subscribe')
        self._notify_listeners(ChannelId.META_SUBSCRIBE, message)
        self._notify_listeners(ChannelId.META_UNSUCCESSFUL, message)

    def _notify_unsubscribe_failure(self, message):
        self.log.debug('Notifying listeners of failed unsubscribe')
        self._notify_listeners(ChannelId.META_UNSUBSCRIBE, message)
        self._notify_listeners(ChannelId.META_UNSUCCESSFUL, message)

    def _queue_send(self, message):
        self.log.debug('Queueing message for sending: %s' % message)
        if self.is_batching or ClientStatus.is_handshaking(self._status):
            self.log.debug('In batch, adding message to queue')
            self._message_queue.append(message)
        else:
            self.log.debug('Sending message immediately')
            self._send(message)

    def _receive(self, message):
        self.log.debug('Receiving message: %s' % message)
        message = self._apply_incoming_extensions(message)
        if not message:
            self.log.debug('Message cancelled by extensions')
            return
        self._update_advice(message.advice)
        handler = self._handle_message_response
        if message.channel and message.channel.is_meta:
            handler_name = '_handle_%s_response' % '_'.join(message.channel.parts[1:])
            self.log.debug('Looking for handler named %s' % handler_name)
            if hasattr(self, handler_name):
                handler = getattr(self, handler_name)
        self.log.debug('Passing message to handler %s' % handler.__name__)
        handler(message)

    def _reset_backoff_period(self):
        self.log.debug('Resetting backoff period to 0')
        self._backoff_period = 0

    def _send(self, messages, for_setup=False, sync=False):

        # Make sure we got a list of messages
        if not isinstance(messages, (list, tuple)):
            if messages is None:
                messages = []
            else:
                messages = [messages]
        self.log.debug('Sending messages: %s' % messages)

        # Make sure we can send messages
        if not for_setup and self._status not in (ClientStatus.CONNECTING, ClientStatus.CONNECTED):
            self.log.debug('Client is not connected, cannot send messages')
            self._handle_failure(messages, errors.StatusError(self._status))
            return False

        # Prepare the messages by checking that they all have a client ID and
        # passing them through the outgoing extensions. We check for client IDs
        # since messages could have been generated before the handshake
        # completed and the client ID was known.
        prepared_messages = []
        for message in messages:
            if self._client_id:
                message['clientId'] = self._client_id
            message = self._apply_outgoing_extensions(message)
            if not message:
                continue
            message.id = str(self._get_next_message_id())
            prepared_messages.append(message)
        if not prepared_messages:
            self.log.debug('All messages cancelled by extensions, skipping send')
            return False

        # Pass off the messages to the transport
        self.log.debug('Prepared messages: %s' % prepared_messages)
        self._transport.send(prepared_messages, sync=sync)
        return True

    def _set_status(self, status):
        if status == self._status:
            return
        self.log.info('Status: %s -> %s' % (self._status, status))
        self._status = status

    def _update_advice(self, new_advice):
        if new_advice:
            advice = self._options['advice'].copy()
            advice.update(new_advice)
            self._advice = advice
            self.log.debug('New advice: %s' % self._advice)

    def clear_subscriptions(self):
        self.log.info('Clearing subscriptions')
        for channel in self._channels.values():
            channel.clear_subscriptions()

    def configure(self, **options):
        if not options:
            return
        self._options.update(options)
        self.log.debug('Options changed to: %s' % self._options)

    def disconnect(self, properties=None, sync=True):
        if self.is_disconnected:
            self.log.debug('Client already disconnected, skipping disconnect')
            return
        message = Message(properties, channel=ChannelId.META_DISCONNECT)
        self.log.debug('Sending disconnect: %s' % message)
        self._set_status(ClientStatus.DISCONNECTING)
        self._send(message, for_setup=True, sync=sync)

    def end_batch(self):
        if self._batch_id == 0:
            raise errors.BatchError()
        self.log.debug('Ended batch with ID %s' % self._batch_id)
        self._batch_id -= 1
        if not self.is_batching and not self.is_disconnected:
            self.flush_batch()

    def fail_messages(self, messages, exception=None):
        self.log.debug('Failing messages: %s' % messages)
        self._handle_failure(messages, exception)

    def fire(self, event, *args, **kwargs):
        self.log.debug('Firing event %s' % event)
        for listener in self._event_listeners.get(event, []):
            try:
                self.log.debug('Invoking callback "%s" for event %s' %
                               (listener.function.__name__, event))
                final_args = args
                final_kwargs = kwargs
                if listener.extra_args:
                    final_args += listener.extra_args
                if listener.extra_kwargs:
                    final_kwargs = final_kwargs.copy()
                    final_kwargs.update(listener.extra_kwargs)
                listener.function(self, *final_args, **final_kwargs)
            except Exception as ex:
                self.log.warn('Exception with listener "%s" for event %s: %s' %
                              (listener.function.__name__, event, ex))

    def flush_batch(self):
        self.log.debug('Flushing batch of %d messages' % len(self._message_queue))
        if not self._message_queue:
            self.log.debug('No messages in batch queue, skipping flush')
            return
        messages = self._message_queue[:]
        self._message_queue = []
        self._send(messages)

    def get_channel(self, channel_id):
        self.log.debug('Fetching channel %s' % channel_id)
        channel_id = ChannelId.convert(channel_id)
        channel = self._channels.get(channel_id)
        if not channel:
            self.log.debug('Channel does not exist, creating with ID %s' % channel_id)
            channel = Channel(self, channel_id)
            self._channels[channel_id] = channel
        return channel

    def get_known_transports(self):
        self.log.debug('Fetching known transports')
        return self._transports.get_known_transports()

    def get_transport(self, name):
        self.log.debug('Getting transport with name "%s"' % name)
        return self._transports.get_transport(name)

    def handshake(self, properties=None):
        self.log.debug('Initiating client handshake')
        self._set_status(ClientStatus.DISCONNECTED)
        self._handshake(properties=properties)

    def initialize(self, properties=None, **options):
        self.log.debug('Initializing client with options: %s' % options)
        self.configure(**options)
        self.handshake(properties=properties)

    def receive_messages(self, messages):
        self.log.info('Received %d messages' % len(messages))
        list(map(self._receive, messages))

    def register_extension(self, extension):
        self._extensions.append(extension)
        self.log.debug('Registered extension %s' % extension)
        extension.register(self)
        return True

    def register_listener(self, event, function, *extra_args, **extra_kwargs):
        self.log.debug('Registered "%s" for event %s' % (function.__name__, event))
        self._event_listener_id += 1
        self._event_listeners.setdefault(event, []).append(Listener(
            id=self._event_listener_id,
            function=function,
            extra_args=extra_args,
            extra_kwargs=extra_kwargs
        ))
        return self._event_listener_id

    def register_transport(self, transport):
        if not self._transports.add(transport):
            self.log.warn('Failed to register transport %s' % transport)
            return False
        self.log.debug('Registered transport %s' % transport)
        transport.register(self, url=self._url)
        return True

    def send(self, message):
        self.log.debug('Received message for sending: %s' % message)
        self._queue_send(message)

    def start_batch(self):
        self._batch_id += 1
        self.log.debug('Started batch with ID %s' % self._batch_id)

    def unregister_extension(self, extension):
        if extension not in self._extensions:
            self.log.warn('Failed to unregister extension %s, not registered' % extension)
            return False
        self._extensions.remove(extension)
        extension.unregister()
        self.log.debug('Unregistered extension %s' % extension)
        return True

    def unregister_listener(self, id=None, event=None, function=None):
        if (id is not None) == (event is not None or function is not None):
            raise ValueError('Either id or event/function must be given')
        unregistered = 0
        if id is not None:
            for event, listeners in self._event_listeners.items():
                for index, listener in enumerate(listeners):
                    if listener.id == id:
                        del listeners[index]
                        unregistered = 1
                        break
        elif event is not None:
            listeners = self._event_listeners.get(event, [])
            to_remove = []
            for index, listener in enumerate(listeners):
                if function is None or listener.function == function:
                    to_remove.append(index)
            for index in reversed(to_remove):
                del listeners[index]
            unregistered += len(to_remove)
        else:
            for event, listeners in self._event_listeners.items():
                to_remove = []
                for index, listener in enumerate(listeners):
                    if listener.function == function:
                        to_remove.append(index)
                for index in reversed(to_remove):
                    del listeners[index]
                unregistered += len(to_remove)
        self.log.debug('Unregistered %d listeners' % unregistered)
        return bool(unregistered)

    def unregister_transport(self, name):
        transport = self._transports.remove(name)
        if not transport:
            self.log.warn('Failed to unregister transport %s, not registered' % name)
            return None
        self.log.debug('Unregistered transport %s' % transport)
        transport.unregister()
        return transport

    @contextmanager
    def batch(self):
        self.log.debug('Entered batch context manager')
        self.start_batch()
        try:
            self.log.debug('Waiting for batch content')
            yield
        finally:
            self.end_batch()
            self.log.debug('Exited batch context manager')


def get_client(url, io_loop=None, **options):
    client = Client(url, io_loop=io_loop, **options)
    client.register_transport(LongPollingHttpTransport(io_loop=io_loop))
    return client
