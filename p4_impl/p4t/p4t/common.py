""" This module contains definitions that are used throughout all optimization infrastructure. """
from p4t.p4_support.objects import validate_hlir


class OptimizationError(Exception):
    """ A generic class for exceptions raised as a part of optimization process."""

    def __init__(self, what="optimization error"):
        Exception.__init__(self)
        self.what = what

    def __str__(self):
        return self.what


class OptimizationStepRegistration(type):
    """ A metaclass that works in conjunction with OptimizationStep to register optimization steps. """
    def __init__(cls, name, bases, attrs):
        super(OptimizationStepRegistration, cls).__init__(name, bases, attrs)
        if not hasattr(cls, 'steps'):
            cls.steps = {}
        else:
            if cls.step_name is None:
                raise ValueError('step_name is undefined for %s' % name)
        cls.steps.update({cls.step_name: cls})


class OptimizationStep(object):
    """ The base class from which all optimization steps should inherit.

    Typical definition of an optimization step should look like this:
    ::
        class TestOptimizationStep(OptimizationStep):
            step_name = 'test'

            def optimize(self, data, args):
                ...
    """
    __metaclass__ = OptimizationStepRegistration

    step_name = None

    def optimize(self, data, args):
        """ Performs an optimization step.

        Args:
            data(OptimizationData): Data to performs the optimization on.
            args(str): Additional parameters to an optimization step.
        """
        raise NotImplementedError


class OptimizationData(object):
    """ A class encompassing data necessary for optimizations.

    Attributes:
        hlir: The representation of P4 program.
        vmrs: A dictionary mapping a table_name to VMR (e.g., to p4t.vmrs.bmv2.Bmv2VMR).
    """
    def __init__(self, hlir=None, vmrs=None):
        self.hlir = hlir
        self.vmrs = vmrs

    def validate(self):
        validate_hlir(self.hlir)

