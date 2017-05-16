""" This module defines basic classifier's functionality. """
import collections
import abc


class AbstractBasicClassifier(collections.Sequence):
    """ Classifier that supports various structural transformations.

    For convenience it provides read only sequence-like interface to underlying vmr.

    Attributes:
        vmr: Corresponding VMR.
    """
    def __init__(self, vmr):
        self._vmr = vmr

    def __len__(self):
        return len(self._vmr)

    def __getitem__(self, i):
        """ Returns vmr entry. """
        return self._vmr[i]

    @property
    def default_action(self):
        """ Default VMR's action. """
        return self._vmr.default_action

    @property
    def bit_width(self):
        """ Classifier's bit width."""
        return self._vmr.bit_width

    @abc.abstractmethod
    def subset(self, indices):
        """ Constructs a classifier on a given subset of rules.

        Note, the default action is preserved.

        Args:
            indices: Entry indices that define the required subset of rules.
        """
        pass

    @abc.abstractmethod
    def reorder(self, bits, match_type='ternary'):
        """ Creates a new classifier with classification bits reordered.

        Args:
            bits: Sequence of bit indices that specifies bit ordering.
            match_type: Must be one of the following: 'lpm', 'exact', 'ternary'.
        """

    @property
    def vmr(self):
        """ Classifier's VMR (e.g. p4t.vmrs.simple.SimpleVMR)."""
        return self._vmr

    @staticmethod
    def _vmr_copy_subset(source, destination, indices):
        """ Copies subset of VMR entries into another VMR (as well as default action)."""
        for i in indices:
            destination.append(source[i])
        destination.default_action = source.default_action
