from p4t.common import OptimizationStep
from p4t.utils import Namespace

from p4t.p4_support.infrastructure import P4InfrastructureSupport
from p4t.p4_support.objects import ActionTable
from p4t.classifiers.p4 import P4BasicClassifier, P4MultiGroupClassifier
from p4t.p4_support.utils import redirect_table, chain_tables
from p4t.optimizations.oi_lpm import minimize_num_groups


class LpmOptimizationStep(OptimizationStep):
    step_name = 'lpm'

    def optimize(self, data, args):  # pylint: disable=arguments-differ
        try:
            table_name, = args
        except ValueError:
            raise ValueError("LPM step accepts one argument: lpm <table_name>")

        p4_infra = P4InfrastructureSupport(data.hlir, Namespace('p4t_lpm'))

        classifier = P4BasicClassifier(p4_infra, data.hlir.p4_tables[table_name], data.vmrs[table_name])
        classifiers = minimize_num_groups(classifier)
	if len(classifiers) > 1:
            result = P4MultiGroupClassifier(p4_infra, classifier.table.name, classifiers)
	else:
	    result = classifiers[0]

	setup_table = ActionTable(data.hlir, result.setup_action)
	chain_tables(setup_table, result.entry_point)
        redirect_table(data.hlir, data.hlir.p4_tables[table_name], setup_table)

        del data.vmrs[table_name]
        data.vmrs.update(result.collect_vmrs())
