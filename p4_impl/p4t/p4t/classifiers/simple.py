""" In this module the simple (no metadata attached) classifier's implementations is defined."""

from collections import namedtuple

from p4t.classifiers.abstract import AbstractBasicClassifier
from p4t.vmrs.simple import SimpleVMREntry


class BasicClassifier(AbstractBasicClassifier):
    """ Simple implementation of `BasicClassifierBase` with no additional data. """

    def __init__(self, vmr):
        """ Initializes new instance of `BasicClassifier`.

        Args:
            vmr: Classifier's VMR
        """
        super(BasicClassifier, self).__init__(vmr)

    def subset(self, indices):
        new_vmr = self.vmr.create_instance(bit_width=self.bit_width)
        self._vmr_copy_subset(self.vmr, new_vmr, indices)
        return BasicClassifier(new_vmr)

    def reorder(self, bits, match_type='ternary'):
        return ReorderingClassifier.from_original_vmr(self.vmr, bits)


class MultiGroupClassifier(object):
    """ Classifier that semantically performs combined in a set of classifiers.

    If there are matches in more than one classifier, the action of the highest priority entry is used

    This class presents a sequence interface for the underlying subclassifiers.
    """

    def __init__(self, subclassifiers):
        """ Initializes `MultiGroupClassifier` instance.

        Args:
            subclassifiers: Classifiers each of which constitute a subclassifier.
        """
        self._subclassifiers = subclassifiers

    def __len__(self):
        return len(self._subclassifiers)

    def __getitem__(self, i):
        return self._subclassifiers[i]


class FPCAction(namedtuple('FPCAction', ['vmr_entry'])):
    """ An action that performs false positive check against `vmr_entry` before applying its action.

    Attributes:
        vmr_entry: VMR Entry to be wrapped by FPCAction.
    """

    __slots__ = ()


class ReorderingClassifier(BasicClassifier):
    """ A classifiers that represents the bit-reordering of some other classifier.

    Attributes:
        bits: The sequence of classification bit indices that defines the ordering.
    """
    def __init__(self, bits, vmr=None):
        """ Initializes `ReorderingClassifier`.

        Args:
            bits: A sequence of classification bit indices.
            vmr: An optionally supplied VMR.
        """
        super(ReorderingClassifier, self).__init__(vmr)

        self._bits = list(bits)

    @classmethod
    def from_original_vmr(cls, original_vmr, bits):
        """ Constructs a reordered representation of given VMR.

        Args:
            bits: The sequence of classification bit indices.
            original_vmr: Original VMR from which to construct reordering.

        Returns:
            An instance of ReorderingClassifier.
        """
        vmr = cls._reorder_vmr(original_vmr, bits) if original_vmr is not None else []
        return cls(bits, vmr)

    @staticmethod
    def _reorder_vmr(vmr, bits):
        reordered_vmr = vmr.create_instance(bit_width=len(bits))
        for entry in vmr:
            mask = [entry.mask[j] for j in bits]
            key = [entry.value[j] for j in bits]
            if isinstance(entry.action, FPCAction) or len(bits) == len(entry.mask):
                action = entry.action
            else:
                action = FPCAction(entry)
            reordered_vmr.append(SimpleVMREntry(key, mask, action, entry.priority))

        reordered_vmr.default_action = vmr.default_action
        return reordered_vmr

    def subset(self, indices):
        new_vmr = self.vmr.create_instance(self.bit_width)
        self._vmr_copy_subset(self.vmr, new_vmr, indices)
        return ReorderingClassifier(self.bits, new_vmr)

    def reorder(self, bits, match_type='ternary'):
        return ReorderingClassifier(
            [self.bits[i] for i in bits],
            self._reorder_vmr(self._vmr, bits))

    @property
    def bits(self):
        """ A sequence of classification bit indices."""
        return self._bits
