import pytest

import p4t.vmrs.simple as vmr
import p4t.classifiers.simple as classifiers

from test_cls_generic import TestGenericClassifier


# TODO: unify with test_cls_p4

ENTRIES = [
    vmr.SimpleVMREntry([True, True, False], [True, True, True], 1, 1),
    vmr.SimpleVMREntry([True, False, False], [True, True, False], 2, 2),
    vmr.SimpleVMREntry([False, True, False], [True, False, False], 3, 3)]


SVMR = vmr.SimpleVMR(3, ENTRIES, 4)


@pytest.fixture
def classifier():
    return classifiers.BasicClassifier(SVMR)


class TestBasicClassifier(TestGenericClassifier):
    __test__ = True


@pytest.fixture
def r_classifier():
    return classifiers.ReorderingClassifier([0, 2, 1], SVMR)


class TestReorderClassifier(object):
    def test_from_original_vmr(self):
        r_cls = classifiers.ReorderingClassifier.from_original_vmr(SVMR, [1, 2, 0])
        assert list(r_cls[1].mask) == [ENTRIES[1].mask[i] for i in [1, 2, 0]]
        assert list(r_cls[1].value) == [ENTRIES[1].value[i] for i in [1, 2, 0]]
        assert r_cls.bits == [1, 2, 0]
        assert r_cls.default_action == 4

    def test_from_original_vmr_fpc(self):
        r_cls = classifiers.ReorderingClassifier.from_original_vmr(SVMR, [1, 2])
        assert isinstance(r_cls[0].action, classifiers.FPCAction)
        assert r_cls[0].action.vmr_entry == ENTRIES[0]

    def test_subset(self, r_classifier):
        ss_cls = r_classifier.subset([0, 1])
        assert len(ss_cls) == 2
        assert ss_cls.bits == r_classifier.bits
        assert ss_cls[1] == r_classifier[1]

    def test_reorder(self, r_classifier):
        r_cls = r_classifier.reorder([1, 2])
        assert r_cls.bits == [r_classifier.bits[i] for i in [1, 2]]
        assert r_cls[0].action.vmr_entry == r_classifier[0]

    def test_no_unncecessary_fpc(self, classifier):
        r_cls = classifier.reorder(range(len(classifier)))
        assert not isinstance(r_cls[0].action, classifiers.FPCAction)

    def test_reorder_no_fpc_doubling(self, classifier):
        r_cls_1 = classifier.reorder([1, 2])
        r_cls_2 = r_cls_1.reorder([1, 0])
        assert r_cls_1[0].action.vmr_entry == r_cls_2[0].action.vmr_entry
