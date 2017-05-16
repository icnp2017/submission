from itertools import count


class Namespace(object):
    """ Namespace that provide easy nesting and collision avoidance.

    String can be retrieved by means of a standard `str` built-in.
    """

    def __init__(self, name='', parent=None):
        self._name = name
        self._parent = parent
        self._children = set()

    def create_nested_ns(self, name):
        """ Create nested namespace with a given base name.
        Args:
            name: Base namespace name.

        Returns:
            New instance of Namespace, which name is close to the given one.
        """
        final_name = name
        for i in count(1):
            if final_name not in self._children:
                break
            final_name = '{:s}_{:d}'.format(name, i)
        self._children.add(final_name)
        return Namespace(final_name, self)

    def create_nested_name(self, name):
        return self.create_nested_ns(name).fullname

    @property
    def parent(self):
        """ Parent namespace. """
        return self._parent

    @property
    def name(self):
        return self._name

    @property
    def fullname(self):
        if self._parent is None or not self._parent.fullname:
            return self._name
        else:
            return self._parent.fullname + '_' + self._name
