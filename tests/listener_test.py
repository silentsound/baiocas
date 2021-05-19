from __future__ import absolute_import
from __future__ import unicode_literals

from unittest import TestCase

from baiocas.listener import Listener


class TestListener(TestCase):

    def test_create(self):
        listener = Listener(id=1, function=map, extra_args=[], extra_kwargs={})
        assert listener.id == 1
        assert listener.function == map
        assert listener.extra_args == []
        assert listener.extra_kwargs == {}
