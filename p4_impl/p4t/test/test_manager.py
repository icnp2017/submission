
from p4t.manager import OptimizationManager

# noinspection PyUnresolvedReferences
from classifiers.test_cls_p4 import hlir, vmr, table


def test_manager(hlir, vmr, table):
    manager = OptimizationManager()
    manager.data.hlir = hlir
    manager.data.vmrs = {table.name: vmr}
    manager.optimize('lpm', [table.name])
