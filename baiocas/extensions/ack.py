from base import Extension

from ..channel_id import ChannelId


class AckExtension(Extension):

    FIELD_ACK = 'ack'

    def __init__(self):
        super(AckExtension, self).__init__()
        self._server_supports_acks = False
        self._ack_id = None

    def _get_ack(self, message):
        return message.get(message.FIELD_EXT, {}).get(self.FIELD_ACK)

    def _set_ack(self, message, value):
        message.setdefault(message.FIELD_EXT, {})[self.FIELD_ACK] = value

    def receive(self, message):
        channel = message.channel
        if channel == ChannelId.META_HANDSHAKE:
            if self._get_ack(message):
                self._server_supports_acks = True
            self.log.debug('Server supports acks: %s' % self._server_supports_acks)
        elif self._server_supports_acks and channel == '/meta/connect' and message.successful:
            if isinstance(self._get_ack(message), int):
                self._ack_id = self._get_ack(message)
                self.log.debug('Server sent ACK ID: %s' % self._ack_id)
        return message

    def send(self, message):
        channel = message.channel
        if channel == ChannelId.META_HANDSHAKE:
            self._set_ack(message, self._client.ack_enabled)
            self._ack_id = None
            self.log.debug('Handshake being sent, clearing ACK ID')
        elif self._server_supports_acks and channel == '/meta/connect':
            self._set_ack(message, self._ack_id)
            self.log.debug('Sending ACK ID: %s' % self._ack_id)
        return message
