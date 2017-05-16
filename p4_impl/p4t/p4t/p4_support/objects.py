from collections import namedtuple, OrderedDict

from p4_hlir.hlir.p4_imperatives import p4_action, p4_signature_ref, p4_action_validate_types
from p4_hlir.hlir.p4_headers import p4_header, p4_header_instance, p4_field
from p4_hlir.hlir.p4_tables import p4_table, p4_match_type


class ActionParameter(namedtuple('ActionParameter', ['name', 'type', 'access', 'data_width'])):
    __slots__ = ()

    # noinspection PyShadowingBuiltins
    def __new__(cls, name, type=None, access=None, data_width=None):  # pylint: disable=redefined-builtin
        if not (type and access or data_width):
            raise ValueError('Either type and access (for primitive parameter) or data_width (for non-primitive) must be provided')
        if type is not None:
            new_type = set()
            for tp in type:
                if tp == 'int':
                    new_type.update({int, long})
                elif tp == 'field':
                    new_type.add(p4_field)
                else:
                    raise ValueError('Unknown type: {:s}'.format(tp))
            type = new_type
        return super(ActionParameter, cls).__new__(cls, name, type, access, data_width)

    def is_primitive(self):
        return self.type and self.access


class Action(p4_action):
    def __init__(self, hlir, name, *parameters):
        """ Initializes new P4 action.

        Args:
            hlir(p4_hlir.main.HLIR):
            name: Action's name.
            *parameters: Action's parameters.
        """

        for param in parameters:
            if param.is_primitive():
                raise ValueError('Parameter {:s} is for primitive action only.'.format(param.name))

        signature = [p.name for p in parameters]
        super(Action, self).__init__(hlir, name, signature=signature, call_sequence=[])

        # This is necessary to later call into p4_hlir validate
        self.required_params = len(parameters)
        assert self.valid_obj

    # pylint: disable=no-member
    def add_primitive_call(self, action, *args):
        new_args = []
        for arg in args:  # pylint: disable=consider-using-enumerate
            if isinstance(arg, str):
                if not arg in self.signature:
                    raise ValueError('Arg {:s} is not one of the parameters: {:s}',
                                     arg, ",".join(self.signature))
                new_args.append(p4_signature_ref(self.signature.index(arg)))
            else:
                new_args.append(arg)
        self.call_sequence.append((action, new_args))


class PrimitiveAction(p4_action):
    def __init__(self, hlir, name, *parameters):
        for param in parameters:
            if not param.is_primitive():
                raise ValueError('Parameter {:s} must be a primitive parameter!'.format(param.name))
        signature = [p.name for p in parameters]
        signature_flags = {p.name: {'type': p.type, 'access': p.access} for p in parameters}
        super(PrimitiveAction, self).__init__(
            hlir, name, signature=signature, signature_flags=signature_flags
        )

        # This is necessary to call into p4_hlir validate
        self.required_params = len(parameters)
        assert self.valid_obj


class CompressPrimitiveAction(PrimitiveAction):
    def __init__(self, hlir, k):
        parameters = [ActionParameter('dst', ['field'], 'write')]
        for i in range(k):
            parameters.append(ActionParameter('src{:d}'.format(i), ['field'], 'read'))
            parameters.append(ActionParameter('from{:d}'.format(i), ['int'], 'read'))
            parameters.append(ActionParameter('to{:d}'.format(i), ['int'], 'read'))
        super(CompressPrimitiveAction, self).__init__(hlir, 'compress_{:d}'.format(k), *parameters)


class SetMaxPrimitiveAction(PrimitiveAction):
    def __init__(self, hlir, k):
        parameters = [ActionParameter('dst', ['field'], 'write')]
        for i in range(k):
            parameters.append(ActionParameter('src{:d}'.format(i), ['field'], 'read'))
        super(SetMaxPrimitiveAction, self).__init__(hlir, 'set_max_field_{:d}'.format(k), *parameters)


class Header(p4_header):
    def __init__(self, hlir, name):
        super(Header, self).__init__(
            hlir, name,
            layout=OrderedDict(), attributes=OrderedDict(),
            length=0, max_length=0)
        assert self.valid_obj

        self._instances = []
        self._hlir = hlir

    # pylint: disable=no-member
    def add_field(self, name, width):
        """ Adds new field to the header. """
        # Don't know why this padding is necessary, but p4-hlir for some reason does it

        self.layout.pop('_padding', None)
        self.attributes.pop('_padding', None)

        self.layout[name] = width
        self.attributes[name] = {}
        if sum(self.layout.values()) % 8 != 0:
            self.layout['_padding'] = 8 - (sum(self.layout.values()) % 8)
            self.attributes['_padding'] = {}

        for instance in self._instances:
            instance.recalc_fields()

    def create_instance(self, name, metadata=True):
        instance = HeaderInstance(self._hlir, name, self, metadata)
        self._instances.append(instance)
        return instance


class HeaderInstance(p4_header_instance):
    def __init__(self, hlir, name, header_type, metadata=True):
        super(HeaderInstance, self).__init__(
            hlir, name, header_type=header_type,
            index=None, max_index=None,
            metadata=metadata, initializer={},
            virtual=False
        )
        assert self.valid_obj
        self._hlir = hlir

        self.recalc_fields()

    def get_field(self, name):
        """ Returns header's field by name. """
        return next((x for x in self.fields if x.name == name), None)

    def recalc_fields(self):
        """ Updates field information from the header type.

        Note, only field addition is supported (not counting auxiliary '_padding' field).
        """
        if self.fields and self.fields[-1].name == '_padding':
            self.fields.pop()

        offset = 0
        for name, width in self.header_type.layout.items():
            if self.get_field(name) is None:
                self.fields.append(self._create_field(name, offset))
            offset += width

    def _create_field(self, name, offset):
        return p4_field(
            self._hlir, self, name,
            self.header_type.layout[name],
            self.header_type.attributes[name],
            offset, None
        )


class Table(p4_table):
    _MATCH_TYPE_DICT = {
        'lpm': p4_match_type.P4_MATCH_LPM,
        'ternary': p4_match_type.P4_MATCH_TERNARY,
        'exact': p4_match_type.P4_MATCH_EXACT
    }

    def __init__(self, hlir, name, fields, match_type, actions=None, default_action=None):
        if default_action is not None and len(default_action.signature) != 0:
            raise ValueError('Default action must not have parameters!')
        if match_type not in Table._MATCH_TYPE_DICT:
            raise ValueError('Unknown match type: {:s}, allowed types are: {:s}'
                             .format(match_type, ", ".join(Table._MATCH_TYPE_DICT.keys())))
        match_type = Table._MATCH_TYPE_DICT[match_type]
        if actions is None:
            actions = []

        super(Table, self).__init__(
            hlir, name,
            match_fields=[(field, match_type, None) for field in fields],
            actions=list(actions), 
            default_action=(default_action, []) if default_action is not None else None,
            action_profile=None, max_size=None, min_size=None
        )

        for action in self.actions:
            self.next_[action] = None  # pylint: disable=no-member

    def add_actions_from_table(self, table):
        """ Copies action information from the given table to the current one.

        Note, that control flow information is also preserved, so that effect of
        executing action from this table is exactly the same.

        Args:
            table: P4 table.
        """

        self.actions.extend(table.actions)
        for action in table.actions:
            self.next_[action] = table.next_[action]
        if self.default_action is not None and self.default_action != table.default_action:
            raise ValueError('Default actions are incompatible, mine: {:s}, his: {:s}'.format(self.default_action, table.default_action))
        self.default_action = table.default_action


class ActionTable(Table):
    """ Single default action table. """
    def __init__(self, hlir, action):
        super(ActionTable, self).__init__(hlir, action.name, [], 'exact', [], action)


def validate_hlir(hlir):
    # This flattens call sequence
    p4_action_validate_types(hlir)
