from unittest import TestCase

from baiocas.transports.base import Transport
from baiocas.transports.registry import TransportRegistry


class MockTransport(Transport):

    def __init__(self, name, only_versions=None):
        self.__name = name
        self.__only_versions = only_versions
        self.is_reset = False
        super(MockTransport, self).__init__()

    @property
    def name(self):
        return self.__name

    def accept(self, version):
        if self.__only_versions is None:
            return True
        return version in self.__only_versions

    def reset(self):
        super(MockTransport, self).reset()
        self.is_reset = True


class TestTransportRegistry(TestCase):

    def setUp(self):
        self.registry = TransportRegistry()

    def test_add(self):
        transport = MockTransport('mock-transport')
        assert self.registry.add(transport)
        assert not self.registry.add(transport)
        assert transport.name in self.registry.get_known_transports()

    def test_find_transports(self):
        transport1 = MockTransport('mock-transport-1')
        transport2 = MockTransport('mock-transport-2', only_versions=['1.0'])
        self.registry.add(transport1)
        self.registry.add(transport2)
        transports = self.registry.find_transports('0.9')
        assert len(transports) == 1
        assert transport1.name in transports
        transports = self.registry.find_transports('1.0')
        assert len(transports) == 2
        assert transport1.name in transports
        assert transport2.name in transports

    def test_get_known_transports(self):
        assert len(self.registry.get_known_transports()) == 0
        transport1 = MockTransport('mock-transport-1')
        transport2 = MockTransport('mock-transport-2', only_versions=[])
        self.registry.add(transport1)
        self.registry.add(transport2)
        transports = self.registry.get_known_transports()
        assert len(transports) == 2
        assert transport1.name in transports
        assert transport2.name in transports

    def test_get_transport(self):
        transport = MockTransport('mock-transport')
        self.registry.add(transport)
        assert self.registry.get_transport(transport.name) is transport
        assert self.registry.get_transport('bad-transport') is None
        assert self.registry.get_transport(transport.name.upper()) is None

    def test_negotiate_transport(self):
        transport1 = MockTransport('mock-transport-1')
        transport2 = MockTransport('mock-transport-2', only_versions=['1.0'])
        self.registry.add(transport1)
        self.registry.add(transport2)
        assert self.registry.negotiate_transport([], '0.9') is None
        assert self.registry.negotiate_transport(['bad-transport'], '0.9') is None
        assert self.registry.negotiate_transport([transport1.name, transport2.name], '0.9') is transport1
        assert self.registry.negotiate_transport([transport2.name, transport1.name], '0.9') is transport1
        assert self.registry.negotiate_transport([transport1.name, transport2.name], '1.0') is transport1
        assert self.registry.negotiate_transport([transport2.name, transport1.name], '1.0') is transport2
        assert self.registry.remove(transport1.name) is transport1
        assert self.registry.negotiate_transport([transport1.name, transport2.name], '1.0') is transport2
        assert self.registry.negotiate_transport([transport1.name, transport2.name], '1.1') is None

    def test_remove(self):
        transport = MockTransport('mock-transport')
        assert self.registry.remove('bad-transport') is None
        self.registry.add(transport)
        assert len(self.registry.get_known_transports()) == 1
        assert self.registry.remove(transport.name.upper()) is None
        assert self.registry.remove(transport.name) is transport
        assert self.registry.remove(transport.name) is None
        assert len(self.registry.get_known_transports()) == 0

    def test_reset(self):
        transport1 = MockTransport('mock-transport-1')
        transport2 = MockTransport('mock-transport-2')
        self.registry.reset()
        self.registry.add(transport1)
        self.registry.add(transport2)
        assert not transport1.is_reset
        assert not transport2.is_reset
        self.registry.reset()
        assert transport1.is_reset
        assert transport2.is_reset
