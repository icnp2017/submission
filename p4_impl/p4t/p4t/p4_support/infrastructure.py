""" Modules providing basic building blocks for classifier manipulation. """

from itertools import chain

from p4t.utils import Namespace
import p4t.p4_support.objects as p4


class KeyConstruction(object):
    """ Class that constructs lookup keys from any subset of bits."""

    def __init__(self, p4_infra):
        """ Initializes new key construction entity.

        Args:
            p4_infra (P4InfrastructureSupport): P4 infrastructure.
        """

        self._p4_infra = p4_infra

        self._header = p4.Header(p4_infra.hlir, p4_infra.ns.create_nested_name('keys_t'))
        self._header_instance = self._header.create_instance(p4_infra.ns.create_nested_name('keys'))
        self._header_ns = Namespace()

        self._next_key_idx = 0

    def add(self, name, subkeys):
        """ Constructs new lookup key from provided list of subkeys.

        Args:
            name: Key name.
            subkeys: List of subkeys.
                They must have attributes `field`, `start` and `end`.
        Returns:
            Tuple of P4 field and setup action.
        """

        total_width = sum(end - start for _, start, end in subkeys)
        key_name = self._header_ns.create_nested_name(name)
        self._header.add_field(key_name, total_width)

        key = self._header_instance.get_field(key_name)

        setup_action = p4.Action(self._p4_infra.hlir, self._p4_infra.ns.create_nested_name('compress_' + key_name))
        setup_action.add_primitive_call(
            self._p4_infra.get_compress(len(subkeys)), key, *chain(*subkeys)
        )

        return key, setup_action


class PriorityEncoder(object):
    """ Class that selects the highest priority among multiple provided. """
    PRIORITY_WIDTH = 16

    def __init__(self, p4_infra, ns):
        """ Initializes the PriorityEncoder.

        Args:
            p4_infra (P4InfrastructureSupport):
                P4 program (e.g., bmv2.p4_types.Program).
        """

        self._p4_infra = p4_infra
        self._ns = ns

        self._header = p4.Header(p4_infra.hlir, ns.create_nested_name('prios_t'))
        self._header.add_field('prio', self.PRIORITY_WIDTH)
        self._header_instance = self._header.create_instance(ns.create_nested_name('prios'))
        self._prio = self._header_instance.get_field('prio')
        self._setup_action = p4.Action(p4_infra.hlir, ns.create_nested_name('init_prios'))
        self._set_max_action = None

        self._subprios = []

    def add(self):
        """ Adds one more sub priority field to take a maximum from.

        Returns:
            An action accepting a single value that sets up the sub priority field.
        """
        if self._set_max_action is not None:
            raise RuntimeError("An attempt to add new priority after set_max action was created.")

        idx = len(self._subprios)
        subprio_name = 'prio_{:d}'.format(idx)
        self._header.add_field(subprio_name, self.PRIORITY_WIDTH)
        subprio = self._header_instance.get_field(subprio_name)

        set_prio_action = p4.Action(self._p4_infra.hlir,
                                    self._ns.create_nested_name('set_prio_{:d}'.format(idx)),
                                    p4.ActionParameter('prio', data_width=self.PRIORITY_WIDTH))
        set_prio_action.add_primitive_call(self._p4_infra.get_modify_field(), subprio, 'prio')

        self._setup_action.add_primitive_call(self._p4_infra.get_modify_field(), subprio, 0)

        self._subprios.append(subprio)
        return set_prio_action

    @property
    def prio(self):
        """ A field instance storing the maximal priority value. """
        return self._prio

    @property
    def setup_action(self):
        return self._setup_action

    def create_set_max_priority_action(self):
        """ Sets up an action that performs highest priority selection.

        Returns:
            Action that performs highest priority selection.
        """
        if self._set_max_action is None:
            self._set_max_action = p4.Action(self._p4_infra.hlir, self._ns.create_nested_name('set_max_prio'))
            self._set_max_action.add_primitive_call(self._p4_infra.get_set_max(len(self._subprios)), self._prio, *self._subprios)

        return self._set_max_action


class P4InfrastructureSupport(object):
    """ This class provides some P4 specific support infrastructure.

    For example, primitive actions  (see :py:func:`get_compress` or :py:func:`init_action`).
    Another examples is key construction (see :py:class:`KeyInfrastructure` and :py:func:`keys`).
    """
    NUM_PRIMITIVE_ARGS = 3

    def __init__(self, hlir, ns):
        """ Initializes infrastructure.

        Args:
            hlir: P4 HLIR object.
            ns: Namespace (see :py:class:`p4t.utils.Namespace`)
        """
        self._hlir = hlir
        self._ns = ns
        self._compress_actions = {}
        self._set_max_actions = {}
        self._keys = KeyConstruction(self)

        self._init_action = p4.Action(hlir, ns.create_nested_name('init'))

    @property
    def ns(self):
        """ Returns basic infra's namespace. """
        return self._ns

    def get_compress(self, i):
        """ Returns an action that compresses bits from the given number of fields."""
        if i not in self._compress_actions:
            self._compress_actions[i] = p4.CompressPrimitiveAction(self.hlir, i)
        return self._compress_actions[i]

    def get_set_max(self, i):
        """ Returns an action that selects maximum value from the given number of fields."""
        if i not in self._set_max_actions:
            self._set_max_actions[i] = p4.SetMaxPrimitiveAction(self.hlir, i)
        return self._set_max_actions[i]

    def get_modify_field(self):
        """ Returns action that modifies a given field."""
        return self.hlir.p4_actions['modify_field']

    @property
    def keys(self):
        """ The key management unit (see :py:class:`KeyConstruction`). """
        return self._keys

    def create_priority_encoder(self, ns):
        """ Creates new priority encoder (see :py:class:`PriorityEncoder`).

        Args:
            ns: Namespace, where the priority encoder must reside.
        """
        return PriorityEncoder(self, ns)

    @property
    def hlir(self):
        """ HLIR P4 program representation. """
        return self._hlir
