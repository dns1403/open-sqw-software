"""E-09 / V-05: CLTs belong to closed irreducible classes, not mixtures."""
from dataclasses import dataclass
import numpy as np
from .markov_analysis import MarkovAnalysis
from .markov_statistics import PoissonSolver, PoissonSolution, real_observable
from .states import checked_probabilities


@dataclass(frozen=True)
class ClassStatistics:
    index: int  # order among closed classes, not the SCC id
    class_id: int
    states: tuple[int, ...]
    absorption_probability: float
    reachable: bool
    poisson: PoissonSolution


@dataclass(frozen=True)
class ClasswiseResult:
    classes: tuple[ClassStatistics, ...]
    initial_law: tuple[float, ...]
    initial_transient_mass: float
    reachable_class_indices: tuple[int, ...]
    ensemble_limit_mean: float  # E[mu_selected_class], not a single-path limit
    between_class_variance: float  # persistent variance of the random limit
    global_clt_available: bool
    global_mean: float | None
    global_asymptotic_variance: float | None


class ClasswiseStatistics:
    """Reuse stationary decomposition and one cached factorization per class.

    Multiple reachable classes always retain conditional CLTs. Even equal
    means can produce a mixture of different Gaussian variances. No numeric
    near-equality rule merges classes into a claimed global Gaussian law.
    """

    def __init__(self, transition, **support_options):
        if isinstance(transition, MarkovAnalysis):
            if support_options: raise ValueError('Support policy is already set by MarkovAnalysis.')
            self.chain = transition
        else: self.chain = MarkovAnalysis(transition, **support_options)
        t = self.chain.transition
        self.solvers = tuple(PoissonSolver(t[list(c.states)][:,list(c.states)],
            stationary=c.stationary, support_atol=0) for c in self.chain.closed_classes)

    def analyze(self, observable, initial):
        f = real_observable(observable, self.chain.dimension)
        q = checked_probabilities(initial)
        mixture = self.chain.mixture(q)
        reachable = {c.id for c in self.chain.reachable_closed_classes(q)}
        classes = tuple(ClassStatistics(i,c.id,c.states,float(mixture.class_weights[i]),c.id in reachable,
            self.solvers[i].solve(f[list(c.states)])) for i,c in enumerate(self.chain.closed_classes))
        indices = tuple(c.index for c in classes if c.reachable)
        means = np.array([c.poisson.mean for c in classes])
        # Shift for large common offsets, as in observable centering.
        shifts = means-means[0]
        shift_mean = float(mixture.class_weights @ shifts)
        mean = float(means[0]+shift_mean)
        between = float(mixture.class_weights @ (shifts-shift_mean)**2)
        if not np.isfinite(mean) or not np.isfinite(between):
            raise ValueError('Class statistics overflowed; rescale the observable.')
        single = classes[indices[0]].poisson if len(indices) == 1 else None
        return ClasswiseResult(classes,tuple(q),float(q[list(self.chain.transient_states)].sum()),indices,mean,between,
            single is not None,None if single is None else single.mean,
            None if single is None else single.asymptotic_variance)
