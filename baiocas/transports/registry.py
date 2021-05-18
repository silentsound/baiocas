from __future__ import absolute_import
from __future__ import unicode_literals


class TransportRegistry(object):

    def __init__(self):
        self._transports = {}

    def add(self, transport):
        if transport.name in self._transports:
            return False
        self._transports[transport.name] = transport
        return True

    def find_transports(self, version):
        return [transport.name for transport in list(self._transports.values())
                if transport.accept(version)]

    def get_known_transports(self):
        return list(self._transports.keys())

    def get_transport(self, name):
        return self._transports.get(name)

    def negotiate_transport(self, requested_transports, bayeux_version):
        for requested_transport in requested_transports:
            if requested_transport not in self._transports:
                continue
            transport = self._transports[requested_transport]
            if transport.accept(bayeux_version):
                return transport
        return None

    def remove(self, name):
        if name not in self._transports:
            return None
        transport = self._transports.pop(name)
        return transport

    def reset(self):
        for transport in list(self._transports.values()):
            transport.reset()
