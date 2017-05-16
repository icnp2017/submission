""" This module provides some basic pipeline manipulation functions. """


def chain_tables(*tables):
    """ Forces given tables to unconditionally follow each other in a control flow.

    Args:
        *tables: P4 tables.
    """
    previous = None
    for table in tables:
        if previous is not None:
            previous.base_default_next = table
            for action in previous.actions:
                previous.next_[action] = table

        previous = table


def redirect_table(hlir, original, target):
    for node in hlir.p4_nodes.values():
        if node.base_default_next == original:
            node.base_default_next = target
    for table in hlir.p4_tables.values():
        for action in table.actions:
            if table.next_[action] == original:
                table.next_[action] = target
    for conditional in hlir.p4_conditional_nodes.values():
        if conditional.next_[False] == original:
            conditional.next_[False] = target
        if conditional.next_[True] == original:
            conditional.next_[True] = target


def set_next_from(source, destination):
    if source.actions != destination.actions:
        raise ValueError('Actions must be equal')
    for action in destination.actions:
        destination.next_[action] = source.next_[action]
    destination.base_default_next = source.base_default_next
