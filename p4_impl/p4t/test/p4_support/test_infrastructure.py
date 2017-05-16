import pytest

from p4t.p4_support.infrastructure import P4InfrastructureSupport, KeyConstruction, PriorityEncoder
from p4t.p4_support.objects import validate_hlir
from p4t.utils import Namespace

from ..conftest import load_hlir, ClonedHLIR


@pytest.fixture(scope='module')
def hlir():
    return load_hlir(
        """
        parser start {
            return ingress;
        }

        header_type ht_t {
            fields {
                a : 2;
                b : 2;
            }
        }

        metadata ht_t md;

        action _drop() {
            drop();
        }

        table test_table {
            reads {
                md.a : ternary;
            }
            actions {
                _drop;
            }
        }

        control ingress {
            apply(test_table);
        }
        """
    )


@pytest.fixture
def infra(hlir):
    return P4InfrastructureSupport(ClonedHLIR(hlir), Namespace('test'))


@pytest.fixture
def keys(infra):
    return infra.keys


def test_header_instances(hlir):
    assert hlir.p4_header_instances['md'].fields[0].name == 'a'
    assert hlir.p4_header_instances['md'].fields[1].name == 'b'


def test_key_constructor_result(infra, keys):
    fa = infra.hlir.p4_header_instances['md'].fields[0]
    fb = infra.hlir.p4_header_instances['md'].fields[1]

    new_key, setup_action = keys.add('foo', [(fb, 0, 2), (fa, 0, 1)])
    assert new_key.width == 3
    assert setup_action.call_sequence[0][0] == infra.get_compress(2)
    assert setup_action.call_sequence[0][1][0] == new_key
    assert new_key.name == 'foo'
    assert setup_action.name == 'test_compress_foo'

    validate_hlir(infra.hlir)


def test_key_constructor_hlir(infra, keys):
    fa = infra.hlir.p4_header_instances['md'].fields[0]
    fb = infra.hlir.p4_header_instances['md'].fields[1]

    keys.add('foo', [(fb, 0, 2), (fa, 0, 1)])
    assert 'test_keys_t' in infra.hlir.p4_headers
    assert 'test_keys' in infra.hlir.p4_header_instances
    assert 'foo' in infra.hlir.p4_headers['test_keys_t'].layout
    assert infra.hlir.p4_header_instances['test_keys'].get_field('foo') is not None

    validate_hlir(infra.hlir)


def test_priority_encoder(infra):
    """ Tests basic priority encoder properties.

    Args:
        infra(P4InfrastructureSupport):
    """
    pe = infra.create_priority_encoder(infra.ns.create_nested_ns('cls'))
    assert 'test_cls_prios_t' in infra.hlir.p4_headers
    assert 'test_cls_prios' in infra.hlir.p4_header_instances
    header_instance = infra.hlir.p4_header_instances['test_cls_prios']
    assert header_instance.get_field('prio') is pe.prio
    assert pe.setup_action
    assert len(pe.setup_action.call_sequence) == 0

    validate_hlir(infra.hlir)


def test_priority_encoder_add(infra):
    """
    Args:
        infra (P4InfrastructureSupport):
    """
    pe = infra.create_priority_encoder(infra.ns.create_nested_ns('cls'))
    header_instance = infra.hlir.p4_header_instances['test_cls_prios']
    set_prio = pe.add()
    assert len(pe.setup_action.call_sequence) == 1
    assert pe.setup_action.call_sequence[0][0] == infra.get_modify_field()
    assert [f.name for f in header_instance.fields if f.name != '_padding'] == ['prio', 'prio_0']
    assert 'test_cls_prios.prio_0' in infra.hlir.p4_fields
    assert set_prio.call_sequence[0][0] == infra.get_modify_field()


def test_priority_encoder_set_max(infra):
    """
    Args:
        infra (P4InfrastructureSupport):
    """
    pe = infra.create_priority_encoder(infra.ns.create_nested_ns('cls'))
    header_instance = infra.hlir.p4_header_instances['test_cls_prios']
    set_prio_1 = pe.add()
    set_prio_2 = pe.add()
    assert [f.name for f in header_instance.fields if f.name != '_padding'] == ['prio', 'prio_0', 'prio_1']
    set_max = pe.create_set_max_priority_action()
    assert len(set_max.call_sequence) == 1
    assert set_max.call_sequence[0][0] == infra.get_set_max(2)
    assert set_max.call_sequence[0][1] == [
        pe.prio,
        set_prio_1.call_sequence[0][1][0],
        set_prio_2.call_sequence[0][1][0]]






