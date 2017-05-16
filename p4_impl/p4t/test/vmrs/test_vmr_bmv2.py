import pytest

import bm_runtime.standard.ttypes as bm_types

from test_generic import PROGRAM, TABLE, ACTION, vmr, TestVMRGeneric

from p4t.vmrs.p4 import P4VMRAction
import p4t.vmrs.simple as svmr
import p4t.vmrs.bmv2 as bvmr


@pytest.fixture
def vmr_instance():
    return bvmr.Bmv2VMR(PROGRAM, TABLE)


class TestBmv2VMR(TestVMRGeneric):
    __test__ = True

    def test_add_non_prefix(self, vmr):
        with pytest.raises(ValueError):
            vmr.append(svmr.SimpleVMREntry([True, True, True], [True, False, True], P4VMRAction(ACTION, [4]), 4))


def test_classifiers_by_table():
    entries = [
        bvmr.BmvVMREntry(
            TABLE.name,
            [
                bm_types.BmMatchParam(
                    type=bm_types.BmMatchParamType.LPM,
                    lpm=bm_types.BmMatchParamLPM('1', 1)
                ),
                bm_types.BmMatchParam(
                    type=bm_types.BmMatchParamType.LPM,
                    lpm=bm_types.BmMatchParamLPM('0', 2)
                )],
            'test_action', ['1'],
            bm_types.BmAddEntryOptions(priority=1)),
        bvmr.BmvVMREntry(
            TABLE.name,
            [
                bm_types.BmMatchParam(
                    type=bm_types.BmMatchParamType.LPM,
                    lpm=bm_types.BmMatchParamLPM('0', 1)
                ),
                bm_types.BmMatchParam(
                    type=bm_types.BmMatchParamType.LPM,
                    lpm=bm_types.BmMatchParamLPM('3', 2)
                )],
            'test_action', ['2'],
            bm_types.BmAddEntryOptions(priority=2)),
        bvmr.BmvVMRDefaultEntry(
            'test_aux_table', 'test_action', ['4']
            ),
        bvmr.BmvVMRDefaultEntry(
            TABLE.name, 'test_action', ['4']
            )
        ]
    classifiers = bvmr.Bmv2VMR.vmrs_by_table(entries, PROGRAM)
    assert TABLE.name in classifiers
    classifier = classifiers[TABLE.name]
    assert len(classifier) == 2
    assert classifier[0].value == [True, False, False]
    assert classifier[1].value == [False, True, True]
    assert classifier[0].action.p4_action == PROGRAM.p4_actions['test_action']
    assert classifier.default_action.p4_action == PROGRAM.p4_actions['test_action']
