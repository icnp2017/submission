import abc
import collections


# noinspection PyClassHasNoInit
class AbstractVMR(collections.MutableSequence):
    """ This is an abstract class that defines what VMR in general are.

    Most importantly, VMR is a mutable sequence of VMR entries, where each VMR
    entry is expected to comply with :py:class:`p4t.vmrs.simple.SimpleVMR`
    interface.
    """
    @abc.abstractproperty
    def bit_width(self):
        """ VMR's bit width. """
        pass

    @abc.abstractproperty
    def default_action(self):
        """ Action to execute on no match."""
        pass

    @default_action.setter
    def default_action(self, value):
        pass

    @abc.abstractmethod
    def create_instance(self, bit_width=None, table=None):
        """ Creates new VMR instance.

        It is a factory method, table must always be supplied for Bmv2VMR.

        Args:
            bit_width: Number of classification bits.
            table: The P4 table corresponding to the new VMR.
        """
        pass
