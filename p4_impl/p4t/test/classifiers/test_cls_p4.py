import pytest

from p4t.vmrs.simple import SimpleVMR
from p4t.vmrs.p4 import P4VMRAction
from p4t.p4_support.objects import validate_hlir
from p4t.p4_support.infrastructure import P4InfrastructureSupport
from p4t.utils import Namespace

import p4t.classifiers.p4 as cls

from ..conftest import create_entry, load_hlir, ClonedHLIR
from test_cls_generic import TestGenericClassifier


@pytest.fixture(scope='module')
def hlir():
    return load_hlir(
        """
        parser start {
            return ingress;
        }

        control ingress {
            apply(test_table);
        }

        header_type test_t {
            fields {
                a : 2;
                b : 2;
                c : 32;
            }
        }

        metadata test_t test;

        action test_action_0(x) {
            modify_field(test.c, x);
        }

        action test_action_1(x) {
            modify_field(test.b, x);
        }

        action _drop() {
            drop();
        }


        table test_table {
            reads {
                test.a : ternary;
                test.b : ternary;
            }
            actions {
                test_action_0;
                test_action_1;
                _drop;
            }
            size: 1024;
        }
        """
    )


@pytest.fixture
def infra(hlir):
    return P4InfrastructureSupport(ClonedHLIR(hlir), Namespace('test'))


@pytest.fixture
def table(hlir):
    return hlir.p4_tables['test_table']


def test_bits2subkeys(table):
    result = cls.P4ReorderingClassifier._bits2subkeys(
        [field for field, _, _ in table.match_fields], [0, 2]
    )
    assert sum(end - start for _, start, end in result) == 2


def test_infra(infra):
    infra.get_compress(1)
    assert 'compress_1' in infra.hlir.p4_actions
    infra.get_set_max(1)
    assert 'set_max_field_1' in infra.hlir.p4_actions


@pytest.fixture
def vmr(hlir):
    action_0 = hlir.p4_actions['test_action_0']
    action_1 = hlir.p4_actions['test_action_1']
    drop_action = hlir.p4_actions['_drop']

    vmr = SimpleVMR(4)
    vmr.append(create_entry('000*', P4VMRAction(action_0, [1]), 1))
    vmr.append(create_entry('001*', P4VMRAction(action_0, [2]), 2))
    vmr.append(create_entry('*100', P4VMRAction(action_1, [3]), 3))
    vmr.append(create_entry('00**', P4VMRAction(action_0, [4]), 4))
    vmr.append(create_entry('*01*', P4VMRAction(action_1, [5]), 5))
    vmr.append(create_entry('*10*', P4VMRAction(action_1, [6]), 6))
    vmr.append(create_entry('*0**', P4VMRAction(action_0, [7]), 7))
    vmr.default_action = P4VMRAction(drop_action, [4])
    return vmr


@pytest.fixture
def classifier(infra, vmr, table):
    return cls.P4BasicClassifier(infra, table, vmr)


class TestP4Classifier(TestGenericClassifier):
    __test__ = True


class TestP4ReorderingClassifier(object):
    def test_reordering(self, classifier):
        """
        Args:
            classifier(cls.P4BasicClassifier):
        """
        r_cls = classifier.reorder([2, 3, 0, 1])
        assert len(r_cls.table.match_fields) == 1
        assert r_cls.setup_action is not None
        assert r_cls.setup_action.call_sequence[0][0] == classifier.p4_infra.get_compress(2)
        assert r_cls.setup_action.call_sequence[0][1][0] is r_cls.table.match_fields[0][0]

    def test_reordering_two(self, classifier):
        """ Testing that two different classifiers are indeed different

        Args:
            classifier(cls.P4BasicClassifier):
        """
        r_cls_0 = classifier.reorder([2, 3, 0, 1])
        r_cls_1 = classifier.reorder([2, 3, 0, 1])
        assert r_cls_0.table.name != r_cls_1.table.name
        assert str(r_cls_0.table.match_fields[0][0]) != str(r_cls_1.table.match_fields[0][0])

    def test_reordering_control_flow(self, classifier):
        """

        Args:
            classifier(cls.P4BasicClassifier):
        """
        r_cls_0 = classifier.reorder([2, 3, 0, 1])
        for action in r_cls_0.table.actions:
            assert r_cls_0.table.next_[action] == classifier.table.next_[action]
        assert r_cls_0.table.base_default_next == classifier.table.base_default_next

@pytest.fixture
def mg_data(classifier):
    r_cls_0 = classifier.subset([0, 1, 3, 6]).reorder([1, 2, 0, 3])
    r_cls_1 = classifier.subset([2, 4, 5]).reorder([1, 2, 3, 0])
    mg = cls.P4MultiGroupClassifier(classifier.p4_infra, classifier.table.name, [r_cls_0, r_cls_1])
    validate_hlir(classifier.p4_infra.hlir)
    return r_cls_0, r_cls_1, mg


class TestP4MultigroupClassifier(object):
    def test_basics(self, mg_data):
        """ Tests that MG classifiers produces what it is expected to produce."""
        r_cls_0, r_cls_1, mg = mg_data

        assert len(mg) == 2
        assert mg.setup_action is not None
        # two for keys, two for pe
        assert len(mg.setup_action.flat_call_sequence) == 4
        actions = {a for a, _, _ in mg.setup_action.flat_call_sequence}
        assert r_cls_0.p4_infra.get_compress(4) in actions
        assert r_cls_0.p4_infra.get_compress(3) in actions
        assert mg.entry_point == r_cls_0.entry_point
        assert mg.entry_point.base_default_next == r_cls_1.entry_point

    def test_dispatcher(self, mg_data, classifier):
        """ Tests that MG classifiers produces what it is expected to produce."""
        r_cls_0, r_cls_1, mg = mg_data
        dispatcher = mg._dispatcher
        assert len(set(dispatcher.table.actions)) == 3
        assert set(dispatcher.table.actions) == set(classifier.table.actions)

    def test_subvmrs(self, mg_data):
        """ Tests that MG classifiers produces what it is expected to produce."""
        r_cls_0, r_cls_1, mg = mg_data
        for entry in r_cls_0:
            assert 'set_prio' in entry.action.p4_action.name
        for entry in r_cls_1:
            assert 'set_prio' in entry.action.p4_action.name

    def test_collect_vmrs(self, mg_data):
        r_cls_0, r_cls_1, mg = mg_data
        vmrs = mg.collect_vmrs()
        assert len(vmrs) == 3
