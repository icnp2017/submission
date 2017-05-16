from itertools import groupby

from p4t.vmrs.simple import SimpleVMREntry
from p4t.vmrs.p4 import P4VMRAction
from p4t.classifiers.abstract import AbstractBasicClassifier
from p4t.p4_support.utils import chain_tables

import p4t.p4_support.objects as p4


class P4BasicClassifier(AbstractBasicClassifier):
    """ Classifier that is attached to a given P4 table.

    This presents target independent interface for manipulating VMR.
    """

    def __init__(self, p4_infra, table, vmr, setup_action=None):
        """ Construct a classifier VMR optionally supplying entries.

        Args:
            p4_infra: P4 support infrastructure.
            table: P4 table that defines the classifier's attachment point.
            vmr: VMR.
            setup_action: P4 action that has to be executed before classification.
        """
        if sum(field.width for field, _, _ in table.match_fields) != vmr.bit_width:
            raise ValueError('Table must have the same bit width as vmr')
        super(P4BasicClassifier, self).__init__(vmr)

        self._p4_infra = p4_infra
        self._table = table
        self._setup_action = setup_action

    @property
    def setup_action(self):
        return self._setup_action

    @property
    def p4_infra(self):
        return self._p4_infra

    def subset(self, indices):
        new_vmr = self.vmr.create_instance(table=self._table)
        self._vmr_copy_subset(self.vmr, new_vmr, indices)
        return P4BasicClassifier(self.p4_infra, self.table, new_vmr, self.setup_action)

    def reorder(self, bits, match_type='ternary'):
        return P4ReorderingClassifier.from_classifier(self, bits, match_type)

    @property
    def table(self):
        """P4 table."""
        return self._table
    
    @property
    def entry_point(self):
        """ Entry point node to the classifier. """
        return self.table

    def collect_vmrs(self):
        return {self.table: self.vmr}


class P4ReorderingClassifier(P4BasicClassifier):
    """ Classifier that reorders classification bits."""

    def __init__(self, p4_infra, table, bits, vmr, setup_action=None):
        """ Initializes a new reordering classifier from the existing P4 table.

        Args:
            p4_infra: The P4 infrastructure.
            table: The original table.
            bits: The sequence of bit indices to use.
            vmr: VMR.
            setup_action: P4 action that has to be executed before classification.
        """

        super(P4ReorderingClassifier, self).__init__(p4_infra, table, vmr, setup_action)
        self._bits = bits

    def subset(self, indices):
        new_vmr = self.vmr.create_instance()
        print(new_vmr.bit_width, self.vmr.bit_width)
        self._vmr_copy_subset(self.vmr, new_vmr, indices)
        return P4ReorderingClassifier(self.p4_infra, self.table, self.bits, new_vmr, self.setup_action)

    @property
    def bits(self):
        return self._bits

    @classmethod
    def from_classifier(cls, classifier, bits, match_type):
        assert isinstance(classifier, P4BasicClassifier)

        p4_fields = [field for field, _, _ in classifier.table.match_fields]
        table_name = classifier.p4_infra.ns.create_nested_name(classifier.table.name + "_r")

        key, setup_action = classifier.p4_infra.keys.add(
            table_name, cls._bits2subkeys(p4_fields, bits)
        )

        table = p4.Table(classifier.p4_infra.hlir, table_name, [key], match_type)
        table.add_actions_from_table(classifier.table)

        vmr = classifier.vmr.create_instance(table=table)
        for entry in classifier:
            mask = [entry.mask[j] for j in bits]
            key = [entry.value[j] for j in bits]
            vmr.append(SimpleVMREntry(key, mask, entry.action, entry.priority))
        vmr.default_action = classifier.default_action
        return P4ReorderingClassifier(classifier.p4_infra, table, bits, vmr, setup_action)

    @staticmethod
    def _bits2subkeys(fields, bits):
        """ Transforms a sequence of bit indices into a list subkeys.

        Args:
            fields: Sequence of P4 fields that define bits' source.
            bits: Indices of bits that should form new keys.
        """
        bit2field = []
        offsets = []
        for field in fields:
            bit2field.extend([field] * field.width)
            offsets.extend(range(field.width))

        contiguous_bits = []
        for bit in bits:
            if len(contiguous_bits) > 0 and contiguous_bits[-1][-1] + 1 == bit:
                contiguous_bits[-1].append(bit)
            else:
                contiguous_bits.append([bit])

        result = []
        for bits in contiguous_bits:
            field_offset = ((bit2field[x], offsets[x]) for x in bits)
            for _, g in groupby(field_offset, lambda y: y[0].name):
                g = list(g)
                (field, first_bit), (_, last_bit) = g[0], g[-1]
                result.append((field, first_bit, last_bit + 1))
        return result


class P4MultiGroupClassifier(object):
    def __init__(self, p4_infra, name, classifiers):
        """ Initializes Multi-Group classifier.

        First classifier's VMR is used as a factory for auxiliary classifiers.

        Args:
            p4_infra(p4t.p4_support.infrastructure.P4InfrastructureSupport):
                P4 infrastructure.
            name: Classifier's name.
            classifiers(list[P4BasicClassifier]):
                Classifiers that would constitute multi group classifier.
        """
        if len(classifiers) < 2:
            raise ValueError("The number of classifiers must not be less than two")

        self._p4_infra = p4_infra
        self._ns = p4_infra.ns.create_nested_ns(name)

        self._priority_encoder = p4_infra.create_priority_encoder(self._ns)
        self._dispatcher = P4MultiGroupClassifier._create_dispatcher(
            self._ns.create_nested_name('dispatcher'), p4_infra, self._priority_encoder.prio, classifiers[0].vmr
        )

        self._classifiers = []
        self._setup_action = p4.Action(p4_infra.hlir, self._ns.create_nested_name('init'))
        self._setup_action.add_primitive_call(self._priority_encoder.setup_action)
        for classifier in classifiers:
            self._add_subclassifier(classifier)
            self._setup_action.add_primitive_call(classifier.setup_action)

        set_max = p4.ActionTable(p4_infra.hlir, self._priority_encoder.create_set_max_priority_action())

        chain_tables(*(cls.table for cls in classifiers))
        chain_tables(classifiers[-1].table, set_max, self._dispatcher.table)

    @property
    def setup_action(self):
        return self._setup_action

    @property
    def entry_point(self):
        return self._classifiers[0].table

    def collect_vmrs(self):
        result = self._dispatcher.collect_vmrs()
        for classifier in self._classifiers:
            result.update(classifier.collect_vmrs())
        return result

    @staticmethod
    def _create_dispatcher(name, p4_infra, dispatch_key, vmr):
        """ Creates dispatch table+VMR that will perform actions.

        Args:
            name: The name of the dispatcher.
            p4_infra: P4 infrastructure.
            dispatch_key: The key on which to dispatch.
            vmr: VMR to create instance from.

        Returns:
            Tuple of dispatch table and dispatch VMR.
        """
        dispatch_table = p4.Table(p4_infra.hlir, name, [dispatch_key], 'exact')
        return P4BasicClassifier(p4_infra, dispatch_table, vmr.create_instance(table=dispatch_table))

    def _add_subclassifier(self, classifier):
        # TODO: priorities are assumed to be gloablly unique
        self._dispatcher.table.add_actions_from_table(classifier.table)

        set_prio = self._priority_encoder.add()
        classifier.table.actions.append(set_prio)

        for i in range(len(classifier.vmr)):
            entry = classifier.vmr[i]
            self._dispatcher.vmr.append(SimpleVMREntry(
                entry.priority,
                [True] * self._priority_encoder.PRIORITY_WIDTH,
                entry.action, entry.priority, self._priority_encoder.PRIORITY_WIDTH
            ))

            # TODO: I don't like call to to_runtime_data, espsecially the latter
            classifier.vmr[i] = SimpleVMREntry(entry.value, entry.mask, P4VMRAction(set_prio, entry.priority), entry.priority)

        self._classifiers.append(classifier)

    def __getitem__(self, idx):
        return self._classifiers[idx]

    def __len__(self):
        return len(self._classifiers)
