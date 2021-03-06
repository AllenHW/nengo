from nengo.base import NengoObject, NengoObjectParam, ObjView
from nengo.config import Config
from nengo.connection import Connection, LearningRule
from nengo.exceptions import ObsoleteError, ValidationError
from nengo.params import Default, ConnectionDefault, NumberParam, StringParam
from nengo.solvers import SolverParam
from nengo.synapses import SynapseParam


class TargetParam(NengoObjectParam):
    def validate(self, probe, target):
        obj = target.obj if isinstance(target, ObjView) else target
        if not hasattr(obj, 'probeable'):
            raise ValidationError("Type %r is not probeable"
                                  % type(obj).__name__,
                                  attr=self.name, obj=probe)

        # do this after; better to know that type is not Probable first
        if not isinstance(obj, LearningRule):
            super(TargetParam, self).validate(probe, target)


class AttributeParam(StringParam):
    def validate(self, probe, attr):
        super(AttributeParam, self).validate(probe, attr)
        if attr in ('decoders', 'transform'):
            raise ObsoleteError("'decoders' and 'transform' are now combined "
                                "into 'weights'. Probe 'weights' instead.",
                                since="v2.1.0")
        if attr not in probe.obj.probeable:
            raise ValidationError("Attribute %r is not probeable on %s."
                                  % (attr, probe.obj),
                                  attr=self.name, obj=probe)


class ProbeSolverParam(SolverParam):
    def __set__(self, instance, value):
        if value is ConnectionDefault:
            value = Config.default(Connection, 'solver')

        super(ProbeSolverParam, self).__set__(instance, value)

    def validate(self, conn, solver):
        super(ProbeSolverParam, self).validate(conn, solver)
        if solver is not None and solver.weights:
            raise ValidationError("weight solvers only work for ensemble to "
                                  "ensemble connections, not probes",
                                  attr=self.name, obj=conn)


class Probe(NengoObject):
    """A probe is an object that collects data from the simulation.

    This is to be used in any situation where you wish to gather simulation
    data (spike data, represented values, neuron voltages, etc.) for analysis.

    Probes do not directly affect the simulation.

    All Nengo objects can be probed (except Probes themselves).
    Each object has different attributes that can be probed.
    To see what is probeable for each object, print its
    ``probeable`` attribute.

    >>> with nengo.Network():
    ...     ens = nengo.Ensemble(10, 1)
    >>> print(ens.probeable)
    ['decoded_output', 'input']

    Parameters
    ----------
    target : Ensemble, Neurons, Node, or Connection
        The object to probe.

    attr : str, optional (Default: None)
        The signal to probe. Refer to the target's ``probeable`` list for
        details. If None, the first element in the ``probeable`` list
        will be used.
    sample_every : float, optional (Default: None)
        Sampling period in seconds. If None, the ``dt`` of the simluation
        will be used.
    synapse : Synapse, optional (Default: None)
        A synaptic model to filter the probed signal.
    solver : Solver, optional (Default: ``ConnectionDefault``)
        `~nengo.solvers.Solver` to compute decoders
        for probes that require them.
    label : str, optional (Default: None)
        A name for the probe. Used for debugging and visualization.
    seed : int, optional (Default: None)
        The seed used for random number generation.

    Attributes
    ----------
    attr : str or None
        The signal that will be probed. If None, the first element of the
        target's ``probeable`` list will be used.
    sample_every : float or None
        Sampling period in seconds. If None, the ``dt`` of the simluation
        will be used.
    solver : Solver or None
        `~nengo.solvers.Solver` to compute decoders. Only used for probes
        of an ensemble's decoded output.
    synapse : Synapse or None
        A synaptic model to filter the probed signal.
    target : Ensemble, Neurons, Node, or Connection
        The object to probe.
    """

    target = TargetParam('target', nonzero_size_out=True)
    attr = AttributeParam('attr', default=None)
    sample_every = NumberParam(
        'sample_every', default=None, optional=True, low=1e-10)
    synapse = SynapseParam('synapse', default=None)
    solver = ProbeSolverParam('solver', default=ConnectionDefault)

    def __init__(self, target, attr=None, sample_every=Default,
                 synapse=Default, solver=Default, label=Default, seed=Default):
        super(Probe, self).__init__(label=label, seed=seed)
        self.target = target
        self.attr = attr if attr is not None else self.obj.probeable[0]
        self.sample_every = sample_every
        self.synapse = synapse
        self.solver = solver

    def __repr__(self):
        return "<Probe%s at 0x%x of '%s' of %s>" % (
            "" if self.label is None else ' "%s"' % self.label,
            id(self), self.attr, self.target)

    def __str__(self):
        return "<Probe%s of '%s' of %s>" % (
            "" if self.label is None else ' "%s"' % self.label,
            self.attr, self.target)

    @property
    def obj(self):
        """(Nengo object) The underlying Nengo object target."""
        return (self.target.obj if isinstance(self.target, ObjView) else
                self.target)

    @property
    def size_in(self):
        """(int) Dimensionality of the probed signal."""
        return self.target.size_out

    @property
    def size_out(self):
        """(int) Cannot connect from probes, so always 0."""
        return 0

    @property
    def slice(self):
        """(slice) The slice associated with the Nengo object target."""
        return (self.target.slice if isinstance(self.target, ObjView) else
                None)
