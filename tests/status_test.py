from unittest import TestCase

from baiocas.status import ClientStatus


class TestClientStatus(TestCase):

    def test_is_disconnect(self):
        assert not ClientStatus.is_disconnected(ClientStatus.UNCONNECTED)
        assert not ClientStatus.is_disconnected(ClientStatus.HANDSHAKING)
        assert not ClientStatus.is_disconnected(ClientStatus.REHANDSHAKING)
        assert not ClientStatus.is_disconnected(ClientStatus.CONNECTING)
        assert not ClientStatus.is_disconnected(ClientStatus.CONNECTED)
        assert ClientStatus.is_disconnected(ClientStatus.DISCONNECTING)
        assert ClientStatus.is_disconnected(ClientStatus.DISCONNECTED)

    def test_is_handshaking(self):
        assert not ClientStatus.is_handshaking(ClientStatus.UNCONNECTED)
        assert ClientStatus.is_handshaking(ClientStatus.HANDSHAKING)
        assert ClientStatus.is_handshaking(ClientStatus.REHANDSHAKING)
        assert not ClientStatus.is_handshaking(ClientStatus.CONNECTING)
        assert not ClientStatus.is_handshaking(ClientStatus.CONNECTED)
        assert not ClientStatus.is_handshaking(ClientStatus.DISCONNECTING)
        assert not ClientStatus.is_handshaking(ClientStatus.DISCONNECTED)
