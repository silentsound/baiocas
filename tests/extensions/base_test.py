import logging
from unittest import TestCase

from baiocas.extensions.base import Extension


class TestExtension(TestCase):

    def setUp(self):
        self.extension = Extension()

    def test_init(self):
        assert isinstance(self.extension.log, logging.Logger)
        assert self.extension.log.name == 'baiocas.extensions.base.Extension'
        assert self.extension.client is None

    def test_repr(self):
        assert repr(self.extension) == 'Extension'

    def test_name(self):
        assert self.extension.name == 'Extension'

    def test_receive(self):
        message = {'channel': '/test', 'id': '1'}
        new_message = self.extension.receive(message)
        assert new_message is message
        assert new_message == {'channel': '/test', 'id': '1'}

    def test_register(self):
        client = {}
        assert self.extension.client is None
        self.extension.register(client)
        assert self.extension.client is client

    def test_send(self):
        message = {'channel': '/test', 'id': '1'}
        new_message = self.extension.send(message)
        assert new_message is message
        assert new_message == {'channel': '/test', 'id': '1'}

    def test_unregister(self):
        client = {}
        assert self.extension.client is None
        self.extension.unregister()
        assert self.extension.client is None
        self.extension.register(client)
        assert self.extension.client is client
        self.extension.unregister()
        assert self.extension.client is None
