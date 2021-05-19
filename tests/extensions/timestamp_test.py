from __future__ import absolute_import
from __future__ import unicode_literals

from email.utils import formatdate
from unittest import TestCase

from mock import patch

from baiocas.client import Client
from baiocas.extensions import timestamp
from baiocas.message import Message


class TestTimestampExtension(TestCase):

    def setUp(self):
        self.extension = timestamp.TimestampExtension()
        self.client = Client('http://www.example.com')
        self.extension.register(self.client)

    def test_receive(self):
        message = Message(channel='/test')
        assert self.extension.receive(message) is message
        assert message == {'channel': '/test'}

    def test_send(self):
        message = Message(channel='/test')
        with patch.object(timestamp, 'formatdate') as mock_formatdate:
            mock_formatdate.return_value = formatdate(usegmt=True)
            assert self.extension.send(message) is message
        mock_formatdate.assert_called_with(usegmt=True)
        assert message.timestamp == mock_formatdate.return_value
