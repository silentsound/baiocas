import logging
import urlparse

from .. import errors
from ..channel_id import ChannelId
from ..message import Message


class Transport(object):

    DEFAULT_MAXIMUM_NETWORK_DELAY = 10000

    OPTION_MAXIMUM_NETWORK_DELAY = 'maximum_network_delay'

    def __init__(self, **options):
        self.log = logging.getLogger('%s.%s' % (self.__module__, self.name))
        self._client = None
        self.options = options
        self.url = None

    def __repr__(self):
        return self.name

    @property
    def name(self):
        raise NotImplementedError('Must be implemented by child classes')

    @property
    def parsed_url(self):
        return self._parsed_url

    def _get_url(self):
        return self._url

    def _set_url(self, url):
        parsed_url = urlparse.urlparse(url or '')
        if url is not None:
            if not parsed_url.hostname:
                raise errors.ConnectionStringError(url, self)
        self._url = url
        self._parsed_url = parsed_url

    url = property(_get_url, _set_url)

    def abort(self):
        self.log.debug('Transport aborted')

    def accept(self, bayeux_version):
        raise NotImplementedError('Must be implemented by child classes')

    def get_timeout(self, messages):
        timeout = self.options.get(
            self.OPTION_MAXIMUM_NETWORK_DELAY,
            self.DEFAULT_MAXIMUM_NETWORK_DELAY
        )
        if len(messages) == 1 and messages[0].channel == ChannelId.META_CONNECT:
            timeout += (messages[0].advice or {}).get(Message.FIELD_TIMEOUT, 0)
        return timeout

    def register(self, client, url=None):
        self.log.debug('Executing registration callback')
        self._client = client
        self.url = url

    def reset(self):
        self.log.debug('Transport reset')

    def send(self, messages):
        raise NotImplementedError('Must be implemented by child classes')

    def unregister(self):
        self.log.debug('Executing unregistration callback')
        self._client = None
        self.url = None
