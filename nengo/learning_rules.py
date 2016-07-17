import warnings

from nengo.base import NengoObjectParam
from nengo.config import SupportDefaultsMixin
from nengo.exceptions import ValidationError
from nengo.params import FrozenObject, NumberParam, Parameter, Default
from nengo.synapses import Lowpass, SynapseParam
from nengo.utils.compat import is_iterable, itervalues


class ConnectionParam(NengoObjectParam):
    def validate(self, instance, conn):
        from nengo.connection import Connection
        if not isinstance(conn, Connection):
            raise ValidationError("'%s' is not a Connection" % conn,
                                  attr=self.name, obj=instance)
        super(ConnectionParam, self).validate(instance, conn)


class LearningRuleType(FrozenObject, SupportDefaultsMixin):
    """Base class for all learning rule objects.

    To use a learning rule, pass it as a ``learning_rule_type`` keyword
    argument to the `~nengo.Connection` on which you want to do learning.

    Each learning rule exposes two important pieces of metadata that the
    builder uses to determine what information should be stored.

    The ``error_type`` is the type of the incoming error signal. Options are:

    * ``'none'``: no error signal
    * ``'scalar'``: scalar error signal
    * ``'decoded'``: vector error signal in decoded space
    * ``'neuron'``: vector error signal in neuron space

    The ``modifies`` attribute denotes the signal targeted by the rule.
    Options are:

    * ``'encoders'``
    * ``'decoders'``
    * ``'weights'``

    Parameters
    ----------
    learning_rate : float, optional (Default: 1e-6)
        A scalar indicating the rate at which ``modifies`` will be adjusted.

    Attributes
    ----------
    error_type : str
        The type of the incoming error signal. This also determines
        the dimensionality of the error signal.
    learning_rate : float
        A scalar indicating the rate at which ``modifies`` will be adjusted.
    modifies : str
        The signal targeted by the learning rule.
    """

    error_type = 'none'
    modifies = None
    probeable = ()

    learning_rate = NumberParam(
        'learning_rate', low=0, low_open=True, readonly=True, default=1e-6)

    def __init__(self, learning_rate=Default):
        super(LearningRuleType, self).__init__()
        self.learning_rate = learning_rate

    def __repr__(self):
        r = []
        for name, default in self._argreprs:
            value = getattr(self, name)
            if value != default:
                r.append("%s=%r" % (name, value))
        return '%s(%s)' % (self.__class__.__name__, ", ".join(r))

    @property
    def _argreprs(self):
        return (('learning_rate', LearningRuleType.learning_rate.default),)


class PES(LearningRuleType):
    """Prescribed Error Sensitivity learning rule.

    Modifies a connection's decoders to minimize an error signal provided
    through a connection to the connection's learning rule.

    Parameters
    ----------
    learning_rate : float, optional (Default: 1e-4)
        A scalar indicating the rate at which weights will be adjusted.
    pre_synapse : Synapse, optional \
              (Default: ``nengo.synapses.Lowpass(tau=0.005)``)
        Synapse model used to filter the pre-synaptic activities
        (see `~nengo.synapses.Synapse`).

    Attributes
    ----------
    learning_rate : float
        A scalar indicating the rate at which weights will be adjusted.
    pre_synapse : Synapse
        Synapse model used to filter the pre-synaptic activities
        (see `~nengo.synapses.Synapse`).
    """

    error_type = 'decoded'
    modifies = 'decoders'
    probeable = ('error', 'correction', 'activities', 'delta')

    learning_rate = NumberParam(
        'learning_rate', low=0, low_open=True, readonly=True, default=1e-4)
    pre_synapse = SynapseParam(
        'pre_synapse', default=Lowpass(tau=0.005), readonly=True)

    def __init__(self, learning_rate=Default, pre_synapse=Default):
        super(PES, self).__init__(learning_rate)
        if learning_rate is not Default and learning_rate >= 1.0:
            warnings.warn("This learning rate is very high, and can result "
                          "in floating point errors from too much current.")
        self.pre_synapse = pre_synapse

    @property
    def _argreprs(self):
        return (('learning_rate', PES.learning_rate.default),
                ('pre_synapse', PES.pre_synapse.default))


class BCM(LearningRuleType):
    """Bienenstock-Cooper-Munroe learning rule.

    Modifies connection weights as a function of the presynaptic activity
    and the difference between the postsynaptic activity and the average
    postsynaptic activity.

    Parameters
    ----------
    learning_rate : float, optional (Default: 1e-9)
        A scalar indicating the rate at which weights will be adjusted.
    pre_synapse : Synapse, optional \
              (Default: ``nengo.synapses.Lowpass(tau=0.005)``)
        Synapse model used to filter the pre-synaptic activities
        (see `~nengo.synapses.Synapse`).
    post_synapse : Synapse, optional
        Synapse model used to filter the post-synaptic activities
        (see `~nengo.synapses.Synapse`).
        If ``Default``, ``post_synapse`` will be the same as ``pre_synapse``.
    theta_synapse : Synapse, optional \
              (Default: ``nengo.synapses.Lowpass(tau=1.0)``)
        Synapse model used to filter the theta signal
        (see `~nengo.synapses.Synapse`).

    Attributes
    ----------
    learning_rate : float
        A scalar indicating the rate at which weights will be adjusted.
    post_synapse : Synapse
        Synapse model used to filter the post-synaptic activities
        (see `~nengo.synapses.Synapse`).
    pre_synapse : Synapse
        Synapse model used to filter the pre-synaptic activities
        (see `~nengo.synapses.Synapse`).
    theta_synapse : Synapse
        Synapse model used to filter the theta signal
        (see `~nengo.synapses.Synapse`).
    """

    error_type = 'none'
    modifies = 'weights'
    probeable = ('theta', 'pre_filtered', 'post_filtered', 'delta')

    learning_rate = NumberParam(
        'learning_rate', low=0, low_open=True, readonly=True, default=1e-9)
    pre_synapse = SynapseParam(
        'pre_synapse', default=Lowpass(tau=0.005), readonly=True)
    post_synapse = SynapseParam(
        'post_synapse', default=None, readonly=True)
    theta_synapse = SynapseParam(
        'theta_synapse', default=Lowpass(tau=1.0), readonly=True)

    def __init__(self, learning_rate=Default, pre_synapse=Default,
                 post_synapse=Default, theta_synapse=Default):
        super(BCM, self).__init__(learning_rate)
        self.pre_synapse = pre_synapse
        self.post_synapse = (self.pre_synapse if post_synapse is Default
                             else post_synapse)
        self.theta_synapse = theta_synapse

    @property
    def _argreprs(self):
        return (('learning_rate', BCM.learning_rate.default),
                ('pre_synapse', BCM.pre_synapse.default),
                ('post_synapse', self.pre_synapse),
                ('theta_synapse', BCM.theta_synapse.default))


class Oja(LearningRuleType):
    """Oja learning rule.

    Modifies connection weights according to the Hebbian Oja rule, which
    augments typicaly Hebbian coactivity with a "forgetting" term that is
    proportional to the weight of the connection and the square of the
    postsynaptic activity.

    Parameters
    ----------
    learning_rate : float, optional (Default: 1e-6)
        A scalar indicating the rate at which weights will be adjusted.
    pre_synapse : Synapse, optional \
              (Default: ``nengo.synapses.Lowpass(tau=0.005)``)
        Synapse model used to filter the pre-synaptic activities
        (see `~nengo.synapses.Synapse`).
    post_synapse : Synapse, optional
        Synapse model used to filter the post-synaptic activities
        (see `~nengo.synapses.Synapse`).
        If ``Default``, ``post_synapse`` will be the same as ``pre_synapse``.
    beta : float, optional (Default: 1.0)
        A scalar weight on the forgetting term.

    Attributes
    ----------
    beta : float
        A scalar weight on the forgetting term.
    learning_rate : float
        A scalar indicating the rate at which weights will be adjusted.
    post_synapse : Synapse
        Synapse model used to filter the post-synaptic activities
        (see `~nengo.synapses.Synapse`).
    pre_synapse : Synapse
        Synapse model used to filter the pre-synaptic activities
        (see `~nengo.synapses.Synapse`).
    """

    error_type = 'none'
    modifies = 'weights'
    probeable = ('pre_filtered', 'post_filtered', 'delta')

    learning_rate = NumberParam(
        'learning_rate', low=0, low_open=True, readonly=True, default=1e-6)
    pre_synapse = SynapseParam(
        'pre_synapse', default=Lowpass(tau=0.005), readonly=True)
    post_synapse = SynapseParam(
        'post_synapse', default=None, readonly=True)
    beta = NumberParam('beta', low=0, readonly=True, default=1.0)

    def __init__(self, learning_rate=Default, pre_synapse=Default,
                 post_synapse=Default, beta=Default):
        super(Oja, self).__init__(learning_rate)
        self.pre_synapse = pre_synapse
        self.post_synapse = (self.pre_synapse if post_synapse is Default
                             else post_synapse)
        self.beta = beta

    @property
    def _argreprs(self):
        return (('learning_rate', Oja.learning_rate.default),
                ('pre_synapse', Oja.pre_synapse.default),
                ('post_synapse', self.pre_synapse),
                ('beta', Oja.beta.default))


class Voja(LearningRuleType):
    """Vector Oja learning rule.

    Modifies an ensemble's encoders to be selective to its inputs.

    A connection to the learning rule will provide a scalar weight for the
    learning rate, minus 1. For instance, 0 is normal learning, -1 is no
    learning, and less than -1 causes anti-learning or "forgetting".

    Parameters
    ----------
    learning_rate : float, optional (Default: 1e-2)
        A scalar indicating the rate at which encoders will be adjusted.
    post_synapse : Synapse, optional \
              (Default: ``nengo.synapses.Lowpass(tau=0.005)``)
        Synapse model used to filter the post-synaptic activities
        (see `~nengo.synapses.Synapse`).

    Attributes
    ----------
    learning_rate : float
        A scalar indicating the rate at which encoders will be adjusted.
    post_synapse : Synapse
        Synapse model used to filter the post-synaptic activities
        (see `~nengo.synapses.Synapse`).
    """

    error_type = 'scalar'
    modifies = 'encoders'
    probeable = ('post_filtered', 'scaled_encoders', 'delta')

    learning_rate = NumberParam(
        'learning_rate', low=0, low_open=True, readonly=True, default=1e-2)
    post_synapse = SynapseParam(
        'post_synapse', default=Lowpass(tau=0.005), readonly=True)

    def __init__(self, learning_rate=Default, post_synapse=Default):
        super(Voja, self).__init__(learning_rate)
        self.post_synapse = post_synapse

    @property
    def _argreprs(self):
        return (('learning_rate', Voja.learning_rate.default),
                ('post_synapse', Voja.post_synapse.default))


class LearningRuleTypeParam(Parameter):
    def validate(self, instance, rule):
        if is_iterable(rule):
            for r in (itervalues(rule) if isinstance(rule, dict) else rule):
                self.validate_rule(instance, r)
        elif rule is not None:
            self.validate_rule(instance, rule)
        super(LearningRuleTypeParam, self).validate(instance, rule)

    def validate_rule(self, instance, rule):
        if not isinstance(rule, LearningRuleType):
            raise ValidationError(
                "'%s' must be a learning rule type or a dict or "
                "list of such types." % rule, attr=self.name, obj=instance)
        if rule.error_type not in ('none', 'scalar', 'decoded', 'neuron'):
            raise ValidationError(
                "Unrecognized error type %r" % rule.error_type,
                attr=self.name, obj=instance)
        if rule.modifies not in ('encoders', 'decoders', 'weights'):
            raise ValidationError("Unrecognized target %r" % rule.modifies,
                                  attr=self.name, obj=instance)
