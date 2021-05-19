from __future__ import absolute_import
from __future__ import unicode_literals

from unittest import TestCase

from baiocas.channel_id import ChannelId
from baiocas.client import Client
from baiocas.extensions.ack import AckExtension
from baiocas.message import Message


class TestAckExtension(TestCase):

    def setUp(self):
        self.extension = AckExtension()
        self.client = Client('http://www.example.com')
        self.extension.register(self.client)

    def test_init(self):
        assert self.extension.ack_id is None
        assert not self.extension.server_supports_acks

    def test_receive_handshake(self):
        message = Message(channel=ChannelId.META_HANDSHAKE)
        assert self.extension.receive(message) == message
        assert not self.extension.server_supports_acks
        message.ext = {AckExtension.FIELD_ACK: True}
        assert self.extension.receive(message) == message
        assert self.extension.server_supports_acks

    def test_receive_connect(self):

        # Check that nothing happens when no ACK ID is included
        message = Message(channel=ChannelId.META_CONNECT, successful=True)
        assert self.extension.receive(message) is message
        assert self.extension.ack_id is None
        assert not self.extension.server_supports_acks

        # Check that nothing happens when server support is unknown
        message.ext = {AckExtension.FIELD_ACK: 1}
        assert self.extension.receive(message) == message
        assert self.extension.ack_id is None
        assert not self.extension.server_supports_acks

        # Notify the extension that server supports ACKs
        self.extension.receive(Message(
            channel=ChannelId.META_HANDSHAKE,
            ext={AckExtension.FIELD_ACK: True}
        ))

        # Check that the ACK ID is captured
        assert self.extension.server_supports_acks
        assert self.extension.receive(message) == message
        assert self.extension.ack_id == 1

        # Check that the ACK ID is ignored for failed messages
        message.ext[AckExtension.FIELD_ACK] = 2
        message.successful = False
        assert self.extension.receive(message) == message
        assert self.extension.ack_id == 1

        # Check that the ACK ID is ignored if not an integer
        message.ext[AckExtension.FIELD_ACK] = '2'
        message.successful = True
        assert self.extension.receive(message) == message
        assert self.extension.ack_id == 1

        # Check that updates to the ACK ID are captured
        message.ext[AckExtension.FIELD_ACK] = 2
        assert self.extension.receive(message) == message
        assert self.extension.ack_id == 2

    def test_receive_other(self):
        message = Message(channel='/test', ext={AckExtension.FIELD_ACK: 1})
        assert self.extension.receive(message) is message
        assert not self.extension.server_supports_acks
        assert self.extension.ack_id is None

    def test_send_handshake(self):
        message = Message(channel=ChannelId.META_HANDSHAKE)
        assert self.extension.send(message) == message
        assert message.ext[AckExtension.FIELD_ACK]
        assert self.extension.ack_id is None
        self.client.configure(ack_enabled=False)
        assert self.extension.send(message) == message
        assert not message.ext[AckExtension.FIELD_ACK]
        assert self.extension.ack_id is None

    def test_send_connect(self):
        message = Message(channel=ChannelId.META_CONNECT)
        assert self.extension.send(message) == message
        assert not message.ext
        self.extension.receive(Message(
            channel=ChannelId.META_HANDSHAKE,
            ext={AckExtension.FIELD_ACK: True}
        ))
        assert self.extension.send(message) == message
        assert message.ext[AckExtension.FIELD_ACK] is None
        self.extension.receive(Message(
            channel=ChannelId.META_CONNECT,
            successful=True,
            ext={AckExtension.FIELD_ACK: 1}
        ))
        assert self.extension.send(message) == message
        assert message.ext[AckExtension.FIELD_ACK] == 1

    def test_send_other(self):
        message = Message(channel='/test')
        assert self.extension.send(message) == message
        assert message == {'channel': '/test'}
