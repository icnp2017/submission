import pytest

from p4_hlir.hlir.p4_tables import p4_match_type

from p4t.utils import Namespace
from p4t.p4_support.infrastructure import P4InfrastructureSupport
import p4t.p4_support.objects as p4

from ..conftest import load_hlir, ClonedHLIR


@pytest.fixture(scope='module')
def hlir():
    return load_hlir(
        """
        parser start {
            return ingress;
        }
        header_type test_t {
            fields {
                test : 13;
            }
        }

        metadata test_t test;

        action _drop() {
            drop();
        }

        table test {
            reads {
                test.test : ternary;
            }
            actions {
                _drop;
            }
        }

        control ingress {
            apply(test);
        }
        """
    )


@pytest.fixture
def infra(hlir):
    return P4InfrastructureSupport(ClonedHLIR(hlir), Namespace('test'))


def test_action_param_incomplete():
    with pytest.raises(ValueError):
        p4.ActionParameter('pom', type=['field'])


@pytest.fixture
def primitive_parameter():
    return p4.ActionParameter('pom', type=['field'], access='read')


@pytest.fixture
def non_primitive_parameter():
    return p4.ActionParameter('pom', data_width=16)


def test_action_param_primitive(primitive_parameter):
    assert primitive_parameter.is_primitive()


def test_action_param_nonprimitive(non_primitive_parameter):
    assert not non_primitive_parameter.is_primitive()


@pytest.fixture
def primitive_action(primitive_parameter, infra):
    return p4.PrimitiveAction(infra.hlir, 'test', primitive_parameter)


def test_create_action_non_primitive(infra, non_primitive_parameter, primitive_action):
    action = p4.Action(infra.hlir, 'test', non_primitive_parameter)
    action.add_primitive_call(primitive_action, 1)
    assert action.call_sequence == [(primitive_action, [1])]
    assert action.signature == [non_primitive_parameter.name]


def test_create_action_primitive(infra, primitive_parameter):
    action = p4.PrimitiveAction(infra.hlir, 'test', primitive_parameter)
    assert action.call_sequence == []
    assert action.signature == [primitive_parameter.name]
    assert action.signature_flags == {primitive_parameter.name: {'type': primitive_parameter.type, 'access': primitive_parameter.access}}


def test_create_action_non_primitive_error(infra):
    parameter = p4.ActionParameter('pom', type=['field'], access='read')
    with pytest.raises(ValueError):
        p4.Action(infra.hlir, 'test', parameter)


def test_create_action_primitive_error(infra):
    parameter = p4.ActionParameter('pom', data_width=16)
    with pytest.raises(ValueError):
        p4.PrimitiveAction(infra.hlir, 'test', parameter)


def test_table_attributes(infra):
    table = p4.Table(infra.hlir, 'test', [], 'exact')
    assert table.name == 'test'
    assert table.max_size is None
    assert table.default_action == None
    assert table.actions == []


def test_table_match_type(infra):
    table = p4.Table(infra.hlir, 'test', [infra.hlir.p4_header_instances['test'].fields[0]], 'exact')
    assert table.match_fields[0][1] == p4_match_type.P4_MATCH_EXACT


def test_table_match_type_error(infra):
    with pytest.raises(ValueError):
        p4.Table(infra.hlir, 'test', [], 'no-such-type')


def test_table_copy_from(infra):
    action = p4.Action(infra.hlir, 'action_')
    table1 = p4.Table(infra.hlir, 'test', [], 'exact', )
    table2 = p4.Table(infra.hlir, 'test', [], 'ternary', [action], action)
    table1.add_actions_from_table(table2)
    assert table1.actions == [action]
    assert table1.default_action == (action, [])


def test_table_defatul_action_with_params(infra):
    action = p4.Action(infra.hlir, 'action_', p4.ActionParameter('test', data_width=16))
    with pytest.raises(ValueError):
        p4.Table(infra.hlir, 'test', [], 'exact', [], action)


def test_headers(infra):
    header = p4.Header(infra.hlir, 'hi')
    assert 'hi' in infra.hlir.p4_headers
    field = header.add_field('pom', 16)
    assert 'pom' in header.layout
    header_instance = header.create_instance('hihi')
    assert 'hihi' in infra.hlir.p4_header_instances
    assert header_instance.get_field('pom') is not None
    assert [f.name for f in header_instance.fields if f.name != '_padding'] == ['pom']
    header.add_field('pam', 13)
    assert [f.name for f in header_instance.fields if f.name != '_padding'] == ['pom', 'pam']


