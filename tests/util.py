import sys


class ModuleMask(object):
    """Inspired by this Stack Overflow post: http://bit.ly/oxl7Ft."""

    def __init__(self, *modules):
        self.modules = modules
        self.register()

    def find_module(self, fullname, path=None):
        if fullname in self.modules:
            raise ImportError('Mock import failure for %s' % fullname)

    def register(self):
        if self in sys.meta_path:
            return
        sys.meta_path.append(self)
        for module in self.modules:
            if module in sys.modules:
                del sys.modules[module]

    def unregister(self):
        if self not in sys.meta_path:
            return
        sys.meta_path.remove(self)
