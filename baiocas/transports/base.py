from __future__ import absolute_import
from __future__ import unicode_literals

import logging
import urllib.parse

from tornado.ioloop import IOLoop

from baiocas import errors
from baiocas.channel_id import ChannelId
from baiocas.message import Message


class Transport(object):

    DEFAULT_MAXIMUM_NETWORK_DELAY = 10000

    OPTION_MAXIMUM_NETWORK_DELAY = 'maximum_network_delay'

    def __init__(self, io_loop=None, **options):
        self.log = logging.getLogger('%s.%s' % (self.__module__, self.name))
        self.io_loop = io_loop or IOLoop.instance()
        self._client = None
        self._options = {}
        self.url = None
        self.configure(**options)

    def __repr__(self):
        return self.name

    @property
    def name(self):
        raise NotImplementedError('Must be implemented by child classes')

    @property
    def parsed_url(self):
        return self._parsed_url

    @property
    def options(self):
        return self._options.copy()

    def _get_url(self):
        return self._url

    def _set_url(self, url):
        parsed_url = urllib.parse.urlparse(url or '')
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

    def configure(self, **options):
        if not options:
            return
        self._options.update(options)
        self.log.debug('Options changed to: %s' % self._options)

    def get_timeout(self, messages):
        timeout = self._options.get(
            self.OPTION_MAXIMUM_NETWORK_DELAY,
            self.DEFAULT_MAXIMUM_NETWORK_DELAY
        )
        if len(messages) == 1 and messages[0].channel == ChannelId.META_CONNECT:
            advice = messages[0].advice
            if not advice or Message.FIELD_TIMEOUT not in advice:
                advice = self._client.advice
            timeout += advice[Message.FIELD_TIMEOUT]
        return timeout

    def register(self, client, url=None):
        self.log.debug('Executing registration callback')
        self._client = client
        self.url = url

    def reset(self):
        self.log.debug('Transport reset')

    def send(self, messages, sync=False):
        raise NotImplementedError('Must be implemented by child classes')

    def unregister(self):
        self.log.debug('Executing unregistration callback')
        self._client = None
        self.url = None
