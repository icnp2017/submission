""" Contains definitions for BMV2 VMR classes."""

from collections import namedtuple
from itertools import groupby

from bitstring import Bits
from p4_hlir.hlir.p4_tables import p4_match_type
import bm_runtime.standard.ttypes as bm_types

from p4t.vmrs.abstract import AbstractVMR
from p4t.vmrs.p4 import P4VMRAction
from p4t.vmrs.simple import SimpleVMREntry, to_bits


# noinspection PyUnresolvedReferences,PyClassHasNoInit
class BmvVMREntry(namedtuple(
        'BmvVMREntry',
        ['table_name', 'match_key', 'action_name', 'runtime_data', 'options'])):

    """ BMV2 VMR entry.

    This is the tuple of arguments to be supplied to `bm_mt_add_entry` function.

    Attributes:
        table_name: The name of the table to which this VMR is for.
        match_key: The list of BmMatchParam instances specifying the value-mask.
        action_name: The name of the action to execute
        runtime_data: List of action parameters bytes.
        options: Entry options.
    """

    __slots__ = ()

    @staticmethod
    def is_default():
        """Return whether this is a default entry (see VMRDefaultEntry)."""
        return False


# noinspection PyUnresolvedReferences,PyClassHasNoInit
class BmvVMRDefaultEntry(namedtuple(
        'BmvVMRDefaultEntry',
        ['table_name', 'action_name', 'runtime_data'])):

    """ BMV2 default VMR entry.

    This is the tuple of arguments to be supplied to `bm_mt_set_default_action`.

    Attributes:
        table_name: The name of the table to which this VMR is for.
        action_name: The name of the action to execute
        runtime_data: List of action parameters bytes.
    """

    __slots__ = ()

    @staticmethod
    def is_default():
        """ Return whether this is a default entry (see VMRDefaultEntry)."""
        return True


def _check_lengths_match(expected, actual):
    if expected != actual:
        raise ValueError("Expected length {:d}, got  {:d}"
                         .format(expected, actual))


def _to_bytes(value, length):
    """Convert value to bytes.

    Args:
        value: Must be either Bits or bytes or list of bool or int.
        length: The expected bit length of the value.

    """
    if isinstance(value, str):
        return value
    elif isinstance(value, int):
        return (Bits((8 - (length % 8)) % 8) + Bits(int=value, length=length)).bytes
    elif isinstance(value, Bits):
        _check_lengths_match(length, len(value))
        return (Bits((8 - (length % 8)) % 8) + value).bytes
    elif isinstance(value, list):
        _check_lengths_match(length, len(value))
        return (Bits((8 - (length % 8)) % 8) + Bits(value)).bytes
    else:
        raise TypeError("Value {:s} is of unsupported type: {:s}".format(value, type(value)))


def _convert_runtime_data(action):
    """Convert P4 action to runtime data using action parameters information.

    Args:
        action: P4 action.
    """
    return [_to_bytes(value, width) for value, width in zip(action.runtime_data, action.p4_action.signature_widths)]


class Bmv2VMR(AbstractVMR):
    """ Bmv2 VMR representation."""

    def __init__(self, hlir, table, entries=None):
        """ Initializes new Bmv2VMR instance.

        Args:
            hlir: P4 HLIR.
            table: P4 table.
            entries: The list of entries (must be compatible with SVMREntry).
        """

        self._hlir = hlir
        self._table = table
        self._entries = []
        self._default_entry = None
        if entries is not None:
            for entry in entries:
                if self._table.name != entry.table_name:
                    raise ValueError(
                        'Entry table {:s} does not match VMR table {:s}'
                        .format(entry.table_name, table.name)
                    )
                if entry.is_default():
                    self._default_entry = entry
                else:
                    self._entries.append(entry)

    def __getitem__(self, i):
        return self._to_svmr_entry(self._entries[i])

    def __setitem__(self, i, entry):
        self._entries[i] = self._create_entry(entry.value, entry.mask, entry.action, entry.priority)

    def insert(self, i, entry):
        self._entries.insert(i, self._create_entry(entry.value, entry.mask, entry.action, entry.priority))

    def __delitem__(self, i):
        del self._entries[i]

    def __len__(self):
        return len(self._entries)

    @property
    def bit_width(self):
        return sum(field.width for field, _, _ in self._table.match_fields if field.name != '_padding')

    @property
    def default_action(self):
        if self._default_entry is None:
            return None
        action = self._hlir.p4_actions[self._default_entry.action_name]
        return P4VMRAction(action, self._default_entry.runtime_data)

    # noinspection PyMethodOverriding
    @default_action.setter
    def default_action(self, action):
        self._default_entry = BmvVMRDefaultEntry(
            self._table.name, action.p4_action.name, _convert_runtime_data(action)
        )

    def create_instance(self, bit_width=None, table=None):
        if table is None:
            raise ValueError("Table must be provided!")
        return Bmv2VMR(self._hlir, table)

    @staticmethod
    def vmrs_by_table(vmr_entries, hlir):
        """ Constructs VMRs by grouping given entries by table name.

        Args:
            vmr_entries: Source entries (list of BmvVMREntry or BmvVMRDefaultEntry).
            hlir: P4 HLIR.

        Returns:
            Dictionary mapping table name to corresponding vmr.
        """
        vmrs = {}
        vmr_entries = sorted(vmr_entries, key=lambda x: x.table_name)
        for table_name, entries in groupby(vmr_entries, lambda x: x.table_name):
            entries = list(entries)
            vmrs[table_name] = Bmv2VMR(hlir, hlir.p4_tables[table_name], entries)
        return vmrs

    @property
    def bmv2_entries(self):
        """ BMV2 entries list."""
        result = list(self._entries)
        if self._default_entry is not None:
            result.append(self._default_entry)
        return result

    def _create_entry(self, value, mask, action, priority):
        match_key = []
        cur_bit_index = 0

        for field, match_type, _ in self._table.match_fields:
            cur_value = value[cur_bit_index:cur_bit_index + field.width]
            cur_mask = mask[cur_bit_index:cur_bit_index + field.width]

            if match_type == p4_match_type.P4_MATCH_EXACT:
                match_key.append(self._create_exact_subkey(cur_value, cur_mask, field))
            elif match_type == p4_match_type.P4_MATCH_LPM:
                match_key.append(self._create_prefix_subkey(cur_value, cur_mask, field))
            else:
                print(type(match_key))
                raise NotImplementedError("Only exact and prefix matches are supported")
            cur_bit_index += field.width
        return BmvVMREntry(
            self._table.name, match_key, action.p4_action.name,
            _convert_runtime_data(action), bm_types.BmAddEntryOptions(priority=priority))

    @staticmethod
    def _is_prefix(mask):
        """ Tests whether mask is a prefix"""
        return all(mask[i] or not mask[i + 1] for i in range(len(mask) - 1))

    @staticmethod
    def _create_prefix_subkey(value, mask, field):
        """ Constructs prefix subkey.

        Args:
            value: Matching bits, must be a sequence of bool.
            mask: Mask bits, must be a sequence of bool.
            field: field
        """

        if not Bmv2VMR._is_prefix(mask):
            raise ValueError("Key must be prefix!")
        return bm_types.BmMatchParam(
            type=bm_types.BmMatchParamType.LPM,
            lpm=bm_types.BmMatchParamLPM(_to_bytes(value, field.width), sum(mask))
        )

    @staticmethod
    def _create_exact_subkey(value, mask, field):
        """ Constructs exact subkey.

        Args:
            value: Matching bits, must be a sequence of bool.
            mask: Mask bits, must be a sequence of bool.
            field: field
        """
        if False in mask:
            raise ValueError("Key must be exact!")
        return bm_types.BmMatchParam(
            type=bm_types.BmMatchParamType.EXACT,
            exact=bm_types.BmMatchParamExact(_to_bytes(value, field.width))
        )

    def _to_svmr_entry(self, entry):
        """ Converts BMV2 entry to SVMREntry.

        It is required to conform to the `AbstractVMR` interface.

        Args:
            entry(BmvVMREntry): The BMV2 entry.
        """
        key = []
        mask = []
        priority = None

        if not entry.is_default():
            for match_key, (field, _, _) in zip(entry.match_key, self._table.match_fields):
                if match_key.type == bm_types.BmMatchParamType.LPM:
                    key.extend(to_bits(match_key.lpm.key, field.width))
                    mask.extend([True] * match_key.lpm.prefix_length + [False] * (field.width - match_key.lpm.prefix_length))
                elif match_key.type == bm_types.BmMatchParamType.TERNARY:
                    key.extend(to_bits(match_key.ternary.key, field.width))
                    mask.extend(to_bits(match_key.ternary.mask, field.width))
                elif match_key.type == bm_types.BmMatchParamType.EXACT:
                    key.extend(to_bits(match_key.exact.key, field.width))
                    mask.extend([True] * field.width)
                else:
                    raise NotImplementedError
            priority = entry.options.priority
        else:
            length = sum(f.length for f in self._table.fields)
            key = [False] * length
            mask = [False] * length

        return SimpleVMREntry(key, mask, P4VMRAction(self._hlir.p4_actions[entry.action_name], entry.runtime_data), priority)

    def __repr__(self):
        return "\n".join(repr(x) for x in self)
