import pytest

from p4t.vmrs.simple import SimpleVMREntry, SimpleVMR
from p4t.classifiers.simple import BasicClassifier
import p4t.optimizations.oi_lpm as opt

from ..conftest import create_entry


@pytest.fixture
def classifier():
    vmr = SimpleVMR(4)
    vmr.append(create_entry('000*', 1, 1))
    vmr.append(create_entry('001*', 2, 2))
    vmr.append(create_entry('*100', 3, 3))
    vmr.append(create_entry('00**', 4, 4))
    vmr.append(create_entry('*01*', 5, 5))
    vmr.append(create_entry('*10*', 6, 6))
    vmr.append(create_entry('*0**', 7, 7))

    return BasicClassifier(vmr)


class TestCommon(object):
    def test_expand(self):
        exp = opt.expand(SimpleVMREntry([True, False, False], [True, False, True], None, None), [1, 2])
        assert len(exp) == 2
        assert list(exp[0].mask) == [True, True, True]
        assert list(exp[0].value) == [True, True, False]
        assert list(exp[1].value) == [True, False, False]
        assert exp[0].action is None

    def test_expand_none(self):
        entry = SimpleVMREntry([True, False, False], [True, False, True], None, None)
        [exp_entry] = opt.expand(entry, [0, 2])
        assert tuple(exp_entry.value) == tuple(entry.value)
        assert tuple(exp_entry.mask) == tuple(entry.mask)

    def test_chain_to_bits(self):
        assert list(opt._chain2bits([[1], [1, 2]], 3)) == [1, 2, 0]


class TestLPM(object):
    def test_minimize_num_groups(self, classifier):
        sub_clss = opt.minimize_num_groups(classifier)
        assert len(sub_clss) == 2
        actions_0 = {x.action for x in sub_clss[0]}
        actions_1 = {x.action for x in sub_clss[1]}
        assert actions_0 == {1, 2, 4, 7}
        assert actions_1 == {3, 5, 6}

    def test_minimize_num_groups_lpm(self):
        vmr = SimpleVMR(3)
        vmr.append(create_entry('001', 1, 1))
        vmr.append(create_entry('01*', 2, 2))
        vmr.append(create_entry('0**', 3, 3))

        cls = BasicClassifier(vmr)
        sub_cls = opt.minimize_num_groups(cls)
        assert len(sub_cls) == 1

    def test_maximize_coverage_bounded(self, classifier):
        sub_clss, left = opt.maximize_coverage_bounded([classifier], 1)
        assert len(sub_clss) == 1
        assert len(sub_clss[0]) == 5
        assert {x.action for x in sub_clss[0]} == {1, 2, 5, 6, 7}
        assert len(left) == 1
        assert len(left[0]) == 2

# TODO: Equivalence tests
