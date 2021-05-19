import logging


class Extension(object):

    def __init__(self):
        self.log = logging.getLogger('%s.%s' % (self.__module__, self.name))
        self._client = None

    def __repr__(self):
        return self.name

    @property
    def client(self):
        return self._client

    @property
    def name(self):
        return self.__class__.__name__

    def receive(self, message):
        return message

    def register(self, client):
        self.log.debug('Executing registration callback')
        self._client = client

    def send(self, message):
        return message

    def unregister(self):
        self.log.debug('Executing unregistration callback')
        self._client = None
