""" This module presents P4-specific class to work with VMR."""
from collections import namedtuple

from p4t.vmrs.simple import to_bits


# noinspection PyClassHasNoInit
class P4VMRAction(namedtuple('P4VMRAction', ['p4_action', 'runtime_data'])):
    # TODO: Specify the interface for `runtime_data` must have.
    # noinspection PyUnresolvedReferences
    """ P4 Action with parameters already supplied.

        This can be used as an action parameter for SVMREntry, which is recognized by Bmv2VMR.

        To facilitate various forms of runtime_data, special comparison function is implemented.

        Attributes:
            p4_action: The P4 action.
            runtime_data (list): Action parameters.
        """

    def __eq__(self, other):
        if self.p4_action != other.p4_action:
            return False
        for w, (x, y) in zip(self.p4_action.signature_widths, zip(self.runtime_data, other.runtime_data)):
            if to_bits(x, w) != to_bits(y, w):
                return False
        return True

    def __ne__(self, other):
        return not self == other

    __slots__ = ()
