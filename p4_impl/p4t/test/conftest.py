import os

from p4_hlir.main import HLIR

from p4t.vmrs.simple import SimpleVMREntry


def create_entry(ternary_str, action, prio):
    return SimpleVMREntry(
        [bit == '1' for bit in ternary_str], [bit != '*' for bit in ternary_str],
        action, prio
    )


def load_hlir(hlir_src):
    filename = os.path.join(os.getcwd(), 'test.p4')

    with open(filename, 'w+') as p4_tmp_file:
        p4_tmp_file.write(hlir_src)
        p4_tmp_file.close()
    hlir = HLIR(filename)
    hlir.build()
    os.remove('test.p4')
    return hlir


class ClonedHLIR(object):
    def __init__(self, program):
        self.p4_actions = program.p4_actions.copy()
        self.p4_tables = program.p4_tables.copy()
        self.p4_headers = program.p4_headers.copy()
        self.p4_header_instances = program.p4_header_instances.copy()
        self.p4_nodes = program.p4_nodes.copy()
        self.p4_objects = program.p4_objects[:]
        self.p4_fields = program.p4_fields
