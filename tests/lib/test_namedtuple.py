from cPickle import dumps, HIGHEST_PROTOCOL, loads
from mock import patch
from unittest import TestCase
import sys

from baiocas.lib import namedtuple
from ..util import ModuleMask


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
    
    def test_asdict(self):
        point = Point(x=11, y=22)
        d = point._asdict()
        assert d['x'] == 11
        assert Point(**d) == Point(x=11, y=22)

    def test_basic(self):
        assert Point.__doc__ == 'Point(x, y)'
        point = Point(x=11, y=22)
        assert point[0] + point[1] == 33
        x, y = point
        assert (x, y) == (11, 22)
        assert point.x + point.y == 33

    def test_duplicate_fields(self):
        self.assertRaises(ValueError, namedtuple.namedtuple, 'Temp', 'foo foo')

    def test_invalid_names(self):
        self.assertRaises(ValueError, namedtuple.namedtuple, 'Temp', 'foo!')
        self.assertRaises(ValueError, namedtuple.namedtuple, 'Temp!', 'foo')
        self.assertRaises(ValueError, namedtuple.namedtuple, 'Temp', 'def')
        self.assertRaises(ValueError, namedtuple.namedtuple, 'def', 'foo')
        self.assertRaises(ValueError, namedtuple.namedtuple, 'Temp', '0foo')
        self.assertRaises(ValueError, namedtuple.namedtuple, '0Temp', 'foo')
        self.assertRaises(ValueError, namedtuple.namedtuple, 'Temp', '_foo')
        namedtuple.namedtuple('_Temp', 'foo')

    def test_module_update(self):
        Temp = namedtuple.namedtuple('Temp', 'foo')
        assert Temp.__module__ == self.__module__
        with patch.object(namedtuple._sys, '_getframe', mock_signature=True) as mock_get_frame:
            mock_get_frame.side_effect = AttributeError()
            Temp = namedtuple.namedtuple('Temp', 'foo')
        assert Temp.__module__ == 'namedtuple_Temp'

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

    def test_rename(self):
        fields = ('foo0', '_foo1', 'foo2!', 'foo0', '4foo', 'foo5')
        Temp = namedtuple.namedtuple('Temp', fields, rename=True)
        assert Temp._fields == ('foo0', '_1', '_2', '_3', '_4', 'foo5')

    def test_replace(self):
        point = Point(x=11, y=22)
        assert point._replace(x=100) == Point(x=100, y=22)

    def test_syntax_error(self):
        with patch.object(namedtuple, '_iskeyword') as mock_is_keyword:
            mock_is_keyword.return_value = False
            self.assertRaises(SyntaxError, namedtuple.namedtuple, 'Temp', 'def')

    def test_verbose(self):
        with patch.object(sys, 'stdout', spec_set=True) as mock_stdout:
            Temp = namedtuple.namedtuple('Temp', 'foo', verbose=True)
        call_args_list = mock_stdout.write.call_args_list
        assert len(call_args_list) == 2
        output = [call_args[0][0] for call_args in call_args_list]
        assert output == ["""class Temp(tuple):
            'Temp(foo,)' \n
            __slots__ = () \n
            _fields = ('foo',) \n
            def __new__(_cls, foo,):
                return _tuple.__new__(_cls, (foo,)) \n
            @classmethod
            def _make(cls, iterable, new=tuple.__new__, len=len):
                'Make a new Temp object from a sequence or iterable'
                result = new(cls, iterable)
                if len(result) != 1:
                    raise TypeError('Expected 1 arguments, got %d' % len(result))
                return result \n
            def __repr__(self):
                return 'Temp(foo=%r)' % self \n
            def _asdict(self):
                'Return a new dict which maps field names to their values'
                return dict(zip(self._fields, self)) \n
            def _replace(_self, **kwds):
                'Return a new Temp object replacing specified fields with new values'
                result = _self._make(map(kwds.pop, ('foo',), _self))
                if kwds:
                    raise ValueError('Got unexpected field names: %r' % kwds.keys())
                return result \n
            def __getnewargs__(self):
                return tuple(self) \n
            foo = _property(_itemgetter(0))\n""",
            '\n'
        ]
