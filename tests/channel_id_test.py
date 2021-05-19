from unittest import TestCase

from baiocas.channel_id import ChannelId


class TestChannelId(TestCase):

    def test_constants(self):
        assert ChannelId.META_CONNECT == '/meta/connect'
        assert ChannelId.META_DISCONNECT == '/meta/disconnect'
        assert ChannelId.META_HANDSHAKE == '/meta/handshake'
        assert ChannelId.META_PUBLISH == '/meta/publish'
        assert ChannelId.META_SUBSCRIBE == '/meta/subscribe'
        assert ChannelId.META_UNSUBSCRIBE == '/meta/unsubscribe'
        assert ChannelId.META_UNSUCCESSFUL == '/meta/unsuccessful'

    def test_new(self):
        channel_id = ChannelId()
        assert channel_id == ''
        channel_id = ChannelId('/test')
        assert channel_id == '/test'

    def test_new_with_encoding(self):
        channel_id = ChannelId(b'/caf\xc3\xa9', encoding='utf8')
        assert channel_id == '/caf\xe9'

    def test_new_with_errors(self):
        self.assertRaises(UnicodeDecodeError, ChannelId, b'/caf\xc3', encoding='utf8')
        channel_id = ChannelId(b'/caf\xc3', encoding='utf8', errors='ignore')
        assert channel_id == '/caf'
        channel_id = ChannelId(b'/caf\xc3', encoding='utf8', errors='replace')
        assert channel_id == '/caf\ufffd'

    def test_equal(self):
        channel_id = ChannelId('/test')
        assert channel_id == '/test'
        assert channel_id == '/test'
        assert channel_id != '/Test'
        assert channel_id == ChannelId('/test')
        self.assertRaises(TypeError, channel_id.__eq__, 0)

    def test_is_meta(self):
        assert not ChannelId('/test').is_meta
        assert ChannelId('/meta').is_meta
        assert ChannelId(ChannelId.META).is_meta
        assert not ChannelId('/Meta').is_meta

    def test_is_wild(self):
        assert ChannelId('/test/*').is_wild
        assert ChannelId('/*').is_wild
        assert not ChannelId('/**').is_wild
        assert not ChannelId('*').is_wild

    def test_is_wild_deep(self):
        assert ChannelId('/test/**').is_wild_deep
        assert ChannelId('/**').is_wild_deep
        assert not ChannelId('/*').is_wild_deep
        assert not ChannelId('**').is_wild_deep

    def test_parts(self):
        assert ChannelId('/test').parts == ['test']
        assert ChannelId('/test/some/channel').parts == ['test', 'some', 'channel']
        assert ChannelId().parts == []

    def test_get_wilds(self):
        channel_id = ChannelId('/test/some/channel')
        assert channel_id.get_wilds() == [
            '/test/some/*',
            '/test/some/**',
            '/test/**',
            '/**'
        ]
        channel_id = ChannelId('/')
        assert channel_id.get_wilds() == [
            '/*',
            '/**'
        ]
        channel_id = ChannelId()
        assert channel_id.get_wilds() == []

    def test_convert(self):
        channel_id = ChannelId('/test')
        assert channel_id == ChannelId.convert(channel_id)
        channel_id = ChannelId.convert('/test')
        assert isinstance(channel_id, ChannelId)
        assert channel_id == '/test'
        self.assertRaises(TypeError, ChannelId.convert, 0)
