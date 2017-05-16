import pytest


class TestGenericClassifier(object):
    __test__ = False

    def test_classifier_fixture(self, classifier):
        assert classifier.bit_width == len(classifier[0].value)
        assert hasattr(classifier, 'default_action')

    def test_classifier_subset(self, classifier):
        ss_classifier = classifier.subset([0, 2])
        assert len(ss_classifier) == 2
        assert ss_classifier[:] == [classifier[0], classifier[2]]

    def test_subset_overflow(self, classifier):
        with pytest.raises(IndexError):
            classifier.subset([len(classifier) + 3])

    def test_classifier_reorder(self, classifier):
        bits = [2, 0, 1]
        r_cls = classifier.reorder(bits)
        assert len(r_cls) == len(classifier)
        assert list(r_cls[2].mask) == [classifier[2].mask[i] for i in bits]
        assert list(r_cls[0].value) == [classifier[0].value[i] for i in bits]
        assert r_cls.default_action == classifier.default_action

    def test_classifier_reorder_bad_bit(self, classifier):
        with pytest.raises(IndexError):
            classifier.reorder([classifier.bit_width + 1])
