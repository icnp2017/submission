from collections import namedtuple

from bitstring import Bits

from p4t.vmrs.abstract import AbstractVMR


class SimpleVMREntry(namedtuple('SVMREntry', ['value', 'mask', 'action', 'priority'])):
    """A target independent vmr entry representation.

    Attributes:
        value: The value to be matched against, a sequence of bool.
        mask: The mask to be applied when matching, a sequence of bool.
        action: Action to execute on match.
        priority: Entry priority (if needed).
    """

    __slots__ = ()

    def __new__(cls, value, mask, action, priority, length=None):
        """Construct VMREntry using optional bit length.
        Note, that if the length has been supplied, then value and mask are automatically
        converted to a required format.

        Args:
            value: The value to be matched against (an instance of bitstring.Bits).
            mask: The mask to be applied when matching (an instance of bitstring.Bits).
            action: Action to be executed on match.
            priority: Entry priority (if needed)
            length: Optional bit length.
        """

        if length is not None:
            return super(SimpleVMREntry, cls).__new__(
                cls, to_bits(value, length), to_bits(mask, length), action, priority
            )
        else:
            return super(SimpleVMREntry, cls).__new__(
                cls, value, mask, action, priority
            )

    def is_prefix(self):
        """ Tests whether the SVMREntry is a prefix match."""
        return all(not self.mask[i] or self.mask[i + 1] for i in range(len(self.mask) - 1))

    def is_exact(self):
        """ Tests whether the SVMREntry is an exact match."""
        return all(self.mask)

    def __repr__(self):
        ternary_bits = []
        for value, mask in zip(self.value, self.mask):
            if not mask:
                ternary_bits.append('*')
            elif value:
                ternary_bits.append('1')
            else:
                ternary_bits.append('0')
        return "{:s} => {} ({})".format("".join(ternary_bits), self.action, self.priority)


def _check_lengths_match(expected, actual):
    if expected != actual:
        raise ValueError("Expected length {:d}, got {:d}"
                         .format(expected, actual))


def to_bits(value, length):
    """Convert value to bool sequence.

    Args:
        value: Must be either bits or bytes or int or list.
        length: Bit length of the value.
    """
    if isinstance(value, str):
        return Bits(bytes=value)[-length:]
    elif isinstance(value, int):
        return Bits(int=value, length=length)
    elif isinstance(value, Bits):
        _check_lengths_match(length, len(value))
        return value
    elif isinstance(value, list):
        _check_lengths_match(length, len(value))
        return Bits(value)
    else:
        raise TypeError("Value {:s} is of unsupported type: {:s}".format(value, type(value)))


class SimpleVMR(AbstractVMR):
    """ Target independent VMR with basic validation.

    The only validation it performs is that it checks for the bit width of the supplied entry.

    Attributes:
        default_action: The action that must be executed on NO_MATCH.
    """

    def __init__(self, bit_width, entries=None, default_action=None):
        """ Initializes SimpleVMR instance.

        Args:
            bit_width: Number of classification bits.
            entries: Initial entries (must be compatible with SVMREntry).
            default_action: Action to execute on NO_MATCH.
        """
        self._bit_width = bit_width
        self._entries = []
        self._default_action = default_action
        if entries is not None:
            for entry in entries:
                self.append(entry)

    def insert(self, i, entry):
        self._check_bit_width(len(entry.value))
        self._entries.insert(i, entry)

    def __getitem__(self, i):
        return self._entries[i]

    def __setitem__(self, i, entry):
        self._check_bit_width(len(entry.value))
        self._entries[i] = entry

    def __delitem__(self, i):
        del self._entries[i]

    def __len__(self):
        return len(self._entries)

    @property
    def bit_width(self):
        return self._bit_width

    @property
    def default_action(self):
        return self._default_action

    # noinspection PyMethodOverriding
    @default_action.setter
    def default_action(self, action):
        self._default_action = action

    @classmethod
    def create_instance(cls, bit_width=None, table=None):
        if hasattr(bit_width, 'name'):
            raise ValueError("Table was passed in place of a bit width")
        if bit_width is None and table is None:
            raise ValueError("Either bit width or table must be provided!")
        if bit_width is None:
            bit_width = sum(field.width for field, _, _ in table.match_fields)
        return SimpleVMR(bit_width)

    def _check_bit_width(self, bit_width):
        """ Verifies entry bit width. """
        if bit_width != self._bit_width:
            raise ValueError("Expected bit width {:d}, got {:d}".format(self._bit_width, bit_width))

    def __repr__(self):
        return "\n".join(repr(x) for x in self)
