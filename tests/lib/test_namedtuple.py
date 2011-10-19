from cPickle import dumps, HIGHEST_PROTOCOL, loads
import sys

from baiocas.lib import namedtuple
from tests import ModuleMask, TestCase


class TestNamedTuple(TestCase):

    @classmethod
    def setUpClass(cls):
        cls._mask = ModuleMask('collections')
        reload(namedtuple)
        assert namedtuple.namedtuple.__module__ == 'baiocas.lib.namedtuple'
        module = sys.modules[cls.__module__]
        setattr(module, 'Point', namedtuple.namedtuple('Point', 'x y'))

    @classmethod
    def tearDownClass(cls):
        cls._mask.unregister()
        reload(namedtuple)
        assert namedtuple.namedtuple.__module__ == 'collections'
    
    def test_basic(self):
        assert Point.__doc__ == 'Point(x, y)'
        point = Point(x=11, y=22)
        assert point[0] + point[1] == 33
        x, y = point
        assert (x, y) == (11, 22)
        assert point.x + point.y == 33

    def test_asdict(self):
        point = Point(x=11, y=22)
        d = point._asdict()
        assert d['x'] == 11
        assert Point(**d) == Point(x=11, y=22)

    def test_replace(self):
        point = Point(x=11, y=22)
        assert point._replace(x=100) == Point(x=100, y=22)

    def test_pickling(self):
        point = Point(x=10, y=20)
        assert point == loads(dumps(point, HIGHEST_PROTOCOL))

    def test_override(self):
        
        class CustomPoint(Point):
            
            @property
            def hypot(self):
                return (self.x ** 2 + self.y ** 2) ** 0.5
            
            def __str__(self):
                return 'Point: x=%6.3f y=%6.3f hypot=%6.3f' % (self.x, self.y, self.hypot)
        
        assert str(CustomPoint(3, 4)) == 'Point: x= 3.000 y= 4.000 hypot= 5.000'
        assert str(CustomPoint(14, 5)) == 'Point: x=14.000 y= 5.000 hypot=14.866'
        assert str(CustomPoint(9.0 / 7, 6)) == 'Point: x= 1.286 y= 6.000 hypot= 6.136'
