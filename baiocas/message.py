from json import dumps
from json import loads

from baiocas.channel_id import ChannelId


class Message(dict):
    """
    For more information on subclassing dict so that all updates pass through
    __setitem__, see the following Stack Overflow post: http://bit.ly/dcoFkF.
    """

    FIELD_ADVICE = 'advice'

    FIELD_CHANNEL = 'channel'

    FIELD_CLIENT_ID = 'clientId'

    FIELD_CONNECTION_TYPE = 'connectionType'

    FIELD_DATA = 'data'

    FIELD_ERROR = 'error'

    FIELD_EXT = 'ext'

    FIELD_ID = 'id'

    FIELD_INTERVAL = 'interval'

    FIELD_MINIMUM_VERSION = 'minimumVersion'

    FIELD_RECONNECT = 'reconnect'

    FIELD_SUBSCRIPTION = 'subscription'

    FIELD_SUCCESSFUL = 'successful'

    FIELD_SUPPORTED_CONNECTION_TYPES = 'supportedConnectionTypes'

    FIELD_TIMEOUT = 'timeout'

    FIELD_TIMESTAMP = 'timestamp'

    FIELD_VERSION = 'version'

    RECONNECT_HANDSHAKE = 'handshake'

    RECONNECT_NONE = 'none'

    RECONNECT_RETRY = 'retry'

    def __init__(self, *args, **kwargs):
        for arg in [_f for _f in args if _f]:
            self.update(arg)
        for key, value in kwargs.items():
            setattr(self, key, value)

    def __getattr__(self, name):
        key = self._get_key_from_name(name)
        if key:
            return self.get(key)
        else:
            raise AttributeError(name)

    def __setattr__(self, name, value):
        key = self._get_key_from_name(name)
        if key:
            self.__setitem__(key, value)
        else:
            object.__setattr__(self, name, value)

    def __setitem__(self, key, value):
        if key == self.FIELD_CHANNEL and value is not None:
            value = ChannelId.convert(value)
        dict.__setitem__(self, key, value)

    @property
    def failure(self):
        return not self.successful

    def _get_key_from_name(self, name):
        return getattr(self.__class__, 'FIELD_' + name.upper(), None)

    def copy(self):
        raw_message = super(Message, self).copy()
        return Message(raw_message)

    def setdefault(self, key, value=None):
        if key not in self:
            self[key] = value
        return self[key]

    def update(self, *args, **kwargs):
        if len(args) > 1:
            raise TypeError('update expected at most 1 arguments, got %d' % len(args))
        other = dict(*args, **kwargs)
        for key in other:
            self[key] = other[key]

    @classmethod
    def from_dict(cls, value):
        return Message(value)

    @classmethod
    def from_json(cls, value, encoding=None):
        if encoding is not None:
            value = value.decode(encoding, 'replace')
        messages = loads(value)
        if not isinstance(messages, (list, tuple)):
            messages = [messages]
        return list(map(cls.from_dict, messages))

    @classmethod
    def to_json(cls, messages, encoding=None):
        if not isinstance(messages, (list, tuple)):
            messages = [messages]
        value = dumps(messages, ensure_ascii=False)
        if encoding is not None:
            value = value.encode(encoding)
        return value


class FailureMessage(Message):

    FIELD_EXCEPTION = 'exception'

    FIELD_REQUEST = 'request'

    def __init__(self, *args, **kwargs):
        default_fields = dict(
            successful=False,
            exception=None,
            advice={
                self.FIELD_RECONNECT: self.RECONNECT_NONE,
                self.FIELD_INTERVAL: 0
            }
        )
        super(FailureMessage, self).__init__(default_fields, *args, **kwargs)

    @classmethod
    def from_message(cls, message, exception=None, **kwargs):
        return cls(
            id=message.id,
            channel=message.channel,
            request=message,
            exception=exception,
            **kwargs
        )
