from __future__ import absolute_import
from __future__ import unicode_literals


class ChannelId(str):

    # Prefix for meta channel IDs
    META = '/meta'

    # Connect meta channel ID
    META_CONNECT = META + '/connect'

    # Disconnect meta channel ID
    META_DISCONNECT = META + '/disconnect'

    # Handshake meta channel ID
    META_HANDSHAKE = META + '/handshake'

    # Publish meta channel ID
    META_PUBLISH = META + '/publish'

    # Subscribe meta channel ID
    META_SUBSCRIBE = META + '/subscribe'

    # Unsubscribe meta channel ID
    META_UNSUBSCRIBE = META + '/unsubscribe'

    # Unsuccessful meta channel ID
    META_UNSUCCESSFUL = META + '/unsuccessful'

    # Pattern for wildcard channel IDs
    WILD = '*'

    # Pattern for deep wildcard channel IDs
    WILD_DEEP = '**'

    def __new__(cls, o='', encoding='utf-8', errors='strict'):
        if isinstance(o, bytes):
            return super().__new__(cls, o, encoding=encoding, errors=errors)

        return super().__new__(cls, o)

    def __init__(self, *args, **kwargs):
        self._parts = self.split('/')

    def __hash__(self):
        return super().__hash__()

    def __eq__(self, other):
        if not isinstance(other, str):
            raise TypeError('Expected %s, got %s' % self.__class__, type(other))
        return str.__eq__(self, other)

    @property
    def is_meta(self):
        return self.startswith(self.META)

    @property
    def is_wild(self):
        return self.endswith('/' + self.WILD)

    @property
    def is_wild_deep(self):
        return self.endswith('/' + self.WILD_DEEP)

    @property
    def parts(self):
        return self._parts[1:]

    def get_wilds(self):
        wilds = []
        parts = self._parts
        last_index = len(parts) - 1
        for index in range(last_index, 0, -1):
            name = '/'.join(parts[:index]) + '/*'
            if index == last_index:
                wilds.append(name)
            wilds.append(name + '*')
        return wilds

    @classmethod
    def convert(cls, value):
        if isinstance(value, cls):
            return value
        if not isinstance(value, str):
            raise TypeError('Expected string, got %s' % type(value))
        return cls(value)
