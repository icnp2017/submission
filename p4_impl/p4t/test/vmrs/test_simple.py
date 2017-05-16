import pytest

from test_generic import vmr, TestVMRGeneric

import p4t.vmrs.simple as svmr


def test_check_lengths_match():
    with pytest.raises(ValueError):
        svmr._check_lengths_match(10, 11)


def test_tobits_str():
    assert list(svmr.to_bits('\x11', 8)) == [False, False, False, True, False, False, False, True]


def test_tobits_int():
    assert list(svmr.to_bits(3, 8)) == [False] * 6 + [True] * 2


def test_tobits_list():
    assert svmr.to_bits([True, False, True], 3) == [True, False, True]


def test_tobits_wrong_length():
    with pytest.raises(ValueError):
        svmr.to_bits([True, False, True], 4)


def test_tobits_wrong_type():
    with pytest.raises(TypeError):
        svmr.to_bits({}, 2)


@pytest.fixture
def vmr_instance():
    return svmr.SimpleVMR(3)


class TestSVMR(TestVMRGeneric):
    __test__ = True
    pass
