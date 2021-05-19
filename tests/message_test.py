from email.utils import formatdate
from json import dumps
from unittest import TestCase

from baiocas.channel_id import ChannelId
from baiocas.message import FailureMessage
from baiocas.message import Message


class TestMessage(TestCase):

    def test_constants(self):
        assert Message.RECONNECT_HANDSHAKE == 'handshake'
        assert Message.RECONNECT_NONE == 'none'
        assert Message.RECONNECT_RETRY == 'retry'

    def test_fields(self):
        timestamp = formatdate(usegmt=True)
        message = Message(
            advice={'reconnect': 'none'},
            channel='/test',
            client_id='client-1',
            connection_type='long-polling',
            data='dummy',
            error='402 Client Unauthorized',
            ext={},
            id='1',
            interval=0,
            minimum_version='0.9',
            reconnect='none',
            subscription='/topic',
            supported_connection_types=['long-polling', 'callback-polling'],
            timeout=1000,
            timestamp=timestamp,
            version='1.0'
        )
        assert message == {
            'advice': {'reconnect': 'none'},
            'channel': '/test',
            'clientId': 'client-1',
            'connectionType': 'long-polling',
            'data': 'dummy',
            'error': '402 Client Unauthorized',
            'ext': {},
            'id': '1',
            'interval': 0,
            'minimumVersion': '0.9',
            'reconnect': 'none',
            'subscription': '/topic',
            'supportedConnectionTypes': ['long-polling', 'callback-polling'],
            'timeout': 1000,
            'timestamp': timestamp,
            'version': '1.0'
        }

    def test_init(self):
        message = Message()
        assert message == {}
        message = Message({'channel': '/bad', 'id': '1'}, {'channel': '/test'})
        assert message == {'channel': '/test', 'id': '1'}
        message = Message(channel='/test', id='1')
        assert message == {'channel': '/test', 'id': '1'}
        message = Message({'channel': '/bad', 'id': '1'}, channel='/test')
        assert message == {'channel': '/test', 'id': '1'}

    def test_attribute(self):
        message = Message()
        assert message.channel is None
        message.channel = '/test'
        assert message.channel == '/test'
        assert message == {'channel': '/test'}

    def test_bad_attribute(self):
        message = Message()
        self.assertRaises(AttributeError, getattr, message, 'bad_attribute')
        message.bad_attribute = 'dummy'
        assert message.bad_attribute == 'dummy'
        assert message == {}

    def test_key(self):
        message = Message()
        self.assertRaises(KeyError, message.__getitem__, 'channel')
        message['channel'] = '/test'
        assert message['channel'] == '/test'

    def test_channel(self):
        message = Message({'channel': '/test'})
        assert isinstance(message.channel, ChannelId)
        message = Message(channel='/test')
        assert isinstance(message.channel, ChannelId)
        message = Message()
        message['channel'] = '/test'
        assert isinstance(message.channel, ChannelId)
        message = Message()
        message.channel = '/test'
        assert isinstance(message.channel, ChannelId)

    def test_failure(self):
        message = Message()
        assert message.failure
        message = Message(successful=True)
        assert not message.failure
        message = Message(successful=False)
        assert message.failure
        message['successful'] = True
        assert not message.failure

    def test_copy(self):
        message = Message()
        message_copy = message.copy()
        assert message == message_copy
        assert isinstance(message_copy, Message)
        message = Message(channel='/test', id='1', ext={'ack': True})
        message_copy = message.copy()
        assert message == message_copy
        assert isinstance(message_copy, Message)

    def test_setdefault(self):
        message = Message()
        self.assertRaises(KeyError, message.__getitem__, 'ext')
        assert message.setdefault('ext') is None
        assert message['ext'] is None
        message = Message()
        assert message.setdefault('ext', {}) == {}
        assert message['ext'] == {}
        message = Message(ext={'ack': 1})
        assert message.setdefault('ext', {}) == {'ack': 1}
        assert message['ext'] == {'ack': 1}

    def test_update(self):
        message = Message(channel='/bad1')
        assert message['channel'] == '/bad1'
        message.update({'channel': '/bad2', 'id': '1'}, channel='/test')
        assert message == {'channel': '/test', 'id': '1'}
        self.assertRaises(TypeError, message.update, {'channel': '/bad3'}, {'id': '2'})
        assert message == {'channel': '/test', 'id': '1'}

    def test_from_dict(self):
        message = Message.from_dict({'channel': '/test', 'id': '1'})
        assert message == {'channel': '/test', 'id': '1'}
        assert isinstance(message.channel, ChannelId)

    def test_from_json(self):
        assert Message.from_json(dumps([])) == []
        expected = [{'channel': '/test', 'id': '1'}]
        messages = Message.from_json(dumps(expected[0]))
        assert messages == expected
        for message in messages:
            assert isinstance(message, Message)
        expected = [
            {'channel': '/test1', 'id': '1'},
            {'channel': '/test2', 'id': '2'}
        ]
        messages = Message.from_json(dumps(expected))
        assert messages == expected
        for message in messages:
            assert isinstance(message, Message)

    def test_from_json_with_encoding(self):
        expected = [{'channel': '/caf\xe9', 'id': '1'}]
        value = dumps(expected, ensure_ascii=False).encode('utf8')
        messages = Message.from_json(value, encoding='utf8')
        assert messages == expected
        for message in messages:
            assert isinstance(message, Message)

    def test_to_json(self):
        assert Message.to_json([]) == dumps([])
        message = Message(channel='/test', id='1')
        assert Message.to_json(message) == dumps([message])
        messages = [
            Message(channel='/test1', id='1'),
            Message(channel='/test2', id='2')
        ]
        assert Message.to_json(messages) == dumps(messages)

    def test_to_json_with_encoding(self):
        message = Message(channel='/caf\xe9', id='1')
        value = dumps([message], ensure_ascii=False).encode('utf8')
        assert Message.to_json(message, encoding='utf8') == value


class TestFailureMessage(TestCase):

    def test_fields(self):
        exception = Exception()
        message = FailureMessage(
            exception=exception,
            request={}
        )
        assert message == {
            'successful': False,
            'exception': exception,
            'request': {},
            'advice': {'reconnect': 'none', 'interval': 0}
        }

    def test_init(self):
        message = FailureMessage()
        assert message.failure
        assert message == {
            'successful': False,
            'exception': None,
            'advice': {'reconnect': 'none', 'interval': 0}
        }
        exception = Exception()
        message = FailureMessage({'exception': exception}, successful=True)
        assert not message.failure
        assert message == {
            'successful': True,
            'exception': exception,
            'advice': {'reconnect': 'none', 'interval': 0}
        }

    def test_from_message(self):
        message = Message()
        failure_message = FailureMessage.from_message(message)
        assert isinstance(failure_message, FailureMessage)
        assert failure_message.exception is None
        assert failure_message == {
            'channel': None,
            'id': None,
            'request': message,
            'successful': False,
            'exception': None,
            'advice': {'reconnect': 'none', 'interval': 0}
        }
        message = Message(channel='/test', id='1')
        exception = Exception()
        failure_message = FailureMessage.from_message(
            message,
            exception=exception,
            successful=True
        )
        assert isinstance(failure_message, FailureMessage)
        assert failure_message == {
            'channel': '/test',
            'id': '1',
            'request': message,
            'successful': True,
            'exception': exception,
            'advice': {'reconnect': 'none', 'interval': 0}
        }
