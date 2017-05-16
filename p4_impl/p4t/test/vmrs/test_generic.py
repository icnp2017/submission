import os.path as path

import pytest
from p4_hlir.main import HLIR

import p4t.vmrs.simple as svmr
from p4t.vmrs.p4 import P4VMRAction

PROGRAM = HLIR(path.join(path.dirname(path.realpath(__file__)), "test.p4"))
PROGRAM.build()

ACTION = PROGRAM.p4_actions['test_action']

TABLE = PROGRAM.p4_tables['test_table']

ENTRIES = [
    svmr.SimpleVMREntry([True, True, False], [True, True, True], P4VMRAction(ACTION, [1]), 1),
    svmr.SimpleVMREntry([True, False, False], [True, True, False], P4VMRAction(ACTION, [2]), 2),
    svmr.SimpleVMREntry([False, True, False], [True, False, False], P4VMRAction(ACTION, [3]), 3)
    ]


@pytest.fixture
def vmr(vmr_instance):
    for entry in ENTRIES:
        vmr_instance.append(entry)
    return vmr_instance


class TestVMRGeneric(object):
    __test__ = False

    def compare_entries(self, lhs, rhs):
        assert lhs.value == rhs.value
        assert lhs.mask == rhs.mask
        assert lhs.p4_action == rhs.p4_action
        assert [int(x) for x in lhs.runtime_data] == [int(x) for x in rhs.runtime_data]

    def test_len(self, vmr):
        assert len(vmr) == len(ENTRIES)

    def test_getitem(self, vmr):
        assert list(vmr) == ENTRIES

    def test_add(self, vmr):
        entry = svmr.SimpleVMREntry([True, True, True], [True, True, True], P4VMRAction(ACTION, [4]), 4)
        vmr.append(entry)
        assert vmr[-1].action == entry.action

    def test_create_instance(self, vmr):
        new_vmr = vmr.create_instance(table=TABLE)
        assert len(new_vmr) == 0
        assert new_vmr.default_action is None

    def test_default_action(self, vmr):
        default = P4VMRAction(ACTION, [10])
        vmr.default_action = default
        assert vmr.default_action == default

    def test_bitwidth(self, vmr):
        assert vmr.bit_width == 3

    def test_set_entry(self, vmr):
        entry = svmr.SimpleVMREntry([True, False, True], [True, True, True], P4VMRAction(ACTION, [4]), 4)
        vmr[-1] = entry
        assert vmr[-1] == entry

