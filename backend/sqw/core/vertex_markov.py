"""V-01/V-02/V-04: sparse label reduction of the induced vertex instrument.

P is ROW stochastic: q_next = q @ P. At n>=1, q_n is a preparation-label
law, while q_n @ P is the Born law of the next position measurement.
"""

from dataclasses import dataclass, field
from numbers import Integral
from collections.abc import Mapping

import numpy as np
from scipy.sparse import csc_matrix, csr_matrix, diags

from .states import checked_probabilities, complex_array, validate_state, validate_steps
from .vertex import InducedVertexWalk
from .edge_markov import density_of, frozen_array, Eligibility


def vertex_eligibility(walk, *, fully_observed=True, time_dependent=False,
                       instrument="vertex_measure_and_prepare"):
    reasons = []
    if type(walk) is not InducedVertexWalk:
        reasons.append("requires the validated induced vertex preparation instrument")
    if fully_observed is not True:
        reasons.append("requires every measurement outcome to be observed")
    if time_dependent is not False:
        reasons.append("requires static preparation vectors")
    if instrument != "vertex_measure_and_prepare":
        reasons.append("requires G_x=|chi(x)><x|")
    return Eligibility(not reasons, tuple(reasons))


class VertexReduction:
    """Sparse chi columns and P, with an independent dense Kraus reference.

    Construction takes the existing validated InducedVertexWalk. That reference
    constructor uses dense diagnostic arrays; this reduced model does not keep
    a reference to them. Subsequent storage is O(|V|+|D|).
    """

    def __init__(self, walk: InducedVertexWalk, **contract):
        self.eligibility = vertex_eligibility(walk, **contract)
        self.eligibility.require()
        self.graph, self.dimension = walk.graph, walk.dimension
        rows, cols, values = [], [], []
        for i, x in enumerate(self.graph.vertices):
            for z in (*self.graph.neighbors[x], x):
                j = self.graph.vertex_index[z]
                value = walk.chi[x][j]
                if value != 0:
                    rows.append(j); cols.append(i); values.append(value)
        self._chi = csc_matrix((values, (rows, cols)), shape=(self.dimension, self.dimension))
        squared = self._chi.copy()
        squared.data = abs(squared.data) ** 2
        self._p = squared.T.tocsr()
        self.beta = dict(walk.beta)
        self._analytic_support = walk.analytic_support

    def _weights(self, weights):
        q = checked_probabilities(weights)
        if q.shape != (self.dimension,):
            raise ValueError(f"Vertex label weights must have length {self.dimension}.")
        return q

    def _index(self, label):
        if not isinstance(label, Integral) or isinstance(label, bool) or label not in self.graph.vertex_index:
            raise ValueError("Unknown vertex atom label.")
        return self.graph.vertex_index[label]

    @property
    def analytic_support(self):
        return None if self._analytic_support is None else self._analytic_support.copy()

    @property
    def sparse_P(self):
        """Detached row-stochastic CSR transition matrix."""
        return self._p.copy()

    def transition_matrix(self, *, max_dimension=512):
        if self.dimension > max_dimension:
            raise ValueError("Dense vertex transition diagnostic exceeds max_dimension.")
        return self._p.toarray()

    def apply_P(self, weights):
        """V-02: explicit ROW convention, q @ P (no implicit transpose)."""
        return checked_probabilities(np.asarray(self._weights(weights) @ self._p).ravel())

    def transitions(self, label):
        row = self._p.getrow(self._index(label))
        return np.array([self.graph.vertices[i] for i in row.indices]), checked_probabilities(row.data)

    def atom_ket(self, label):
        return self._chi.getcol(self._index(label)).toarray().ravel()

    def atom_density(self, label):
        return density_of(self.atom_ket(label))

    def atom_born_vertices(self, label):
        return checked_probabilities(self._p.getrow(self._index(label)).toarray().ravel())

    def mean_density(self, weights):
        q = self._weights(weights)
        return (self._chi @ diags(q) @ self._chi.conj().T).toarray()

    def atom_expectations(self, observable):
        a = complex_array(observable, "Observable")
        if a.shape != (self.dimension, self.dimension) or not np.allclose(a, a.conj().T, rtol=0, atol=1e-10):
            raise ValueError("Observable must be Hermitian in the vertex basis.")
        values = np.zeros(self.dimension)
        for i in range(self.dimension):
            col = self._chi.getcol(i)
            values[i] = np.vdot(col.data, a[np.ix_(col.indices, col.indices)] @ col.data).real
        return values

    def with_beta(self, beta: Mapping[int, float]):
        """V-06: reuse P exactly while updating phase-sensitive chi and means."""
        if not isinstance(beta, Mapping) or set(beta) != set(self.graph.vertices):
            raise ValueError("beta must provide exactly every vertex phase.")
        phases = {}
        for x in self.graph.vertices:
            try:
                phase = float(beta[x])
            except (ValueError, TypeError, OverflowError) as error:
                raise ValueError("beta must contain finite real phases.") from error
            if not np.isfinite(phase):
                raise ValueError("beta must contain finite real phases.")
            phases[x] = phase
        result = object.__new__(VertexReduction)
        result.graph, result.dimension, result.eligibility = self.graph, self.dimension, self.eligibility
        result._p = self._p  # invariant even when chi changes
        result._analytic_support = self._analytic_support
        result._chi = self._chi.copy()
        diagonal = np.array([np.exp(1j * phases[x]) * np.sqrt(self._p[i, i]) for i, x in enumerate(self.graph.vertices)])
        result._chi.setdiag(diagonal)
        result._chi.eliminate_zeros()
        result.beta = phases
        return result

    def iter_mean(self, initial, steps):
        count = validate_steps(steps)
        state = frozen_array(validate_state(initial, self.dimension))
        yield VertexMeanState(self, 0, initial=state)
        q = checked_probabilities(abs(state) ** 2 if state.ndim == 1 else np.diag(state).real)
        for step in range(1, count + 1):
            yield VertexMeanState(self, step, label_weights=frozen_array(q))
            if step < count:
                q = self.apply_P(q)


@dataclass(frozen=True)
class VertexMeanState:
    model: VertexReduction = field(repr=False)
    step: int
    label_weights: np.ndarray | None = None
    initial: np.ndarray | None = field(default=None, repr=False)

    def density(self):
        return density_of(self.initial) if self.step == 0 else self.model.mean_density(self.label_weights)

    def born_vertices(self):
        if self.step == 0:
            return checked_probabilities(abs(self.initial) ** 2 if self.initial.ndim == 1 else np.diag(self.initial).real)
        return self.model.apply_P(self.label_weights)

    def purity(self):
        # Nonorthogonal atoms: q @ q is NOT the mean purity (V-06).
        if self.step == 0:
            return 1.0 if self.initial.ndim == 1 else float(np.vdot(self.initial, self.initial).real)
        mean = self.model._chi @ diags(self.label_weights) @ self.model._chi.conj().T
        return float(np.vdot(mean.data, mean.data).real)


@dataclass(frozen=True)
class VertexConditionalState:
    model: VertexReduction = field(repr=False)
    step: int
    outcome: int | None = None
    selected_probability: float | None = None
    log_path_probability: float = 0.0
    initial: np.ndarray | None = field(default=None, repr=False)

    @property
    def stage(self):
        return "initial" if self.step == 0 else "vertex_atom"

    def ket(self):
        if self.step:
            return self.model.atom_ket(self.outcome)
        if self.initial.ndim != 1:
            raise ValueError("Mixed initial state has no stored pure-state ket.")
        return self.initial.copy()

    def density(self):
        return density_of(self.initial) if self.step == 0 else self.model.atom_density(self.outcome)

    def reduced_density(self):
        if not self.step:
            raise ValueError("There has not yet been a measurement.")
        out = np.zeros((self.model.dimension, self.model.dimension), dtype=complex)
        i = self.model._index(self.outcome)
        out[i, i] = 1
        return out

    def born_vertices(self):
        if self.step:
            return self.model.atom_born_vertices(self.outcome)
        return checked_probabilities(abs(self.initial) ** 2 if self.initial.ndim == 1 else np.diag(self.initial).real)

    def purity(self):
        return 1.0 if self.step or self.initial.ndim == 1 else float(np.vdot(self.initial, self.initial).real)


class VertexSession:
    def __init__(self, model, initial, rng):
        self.model, self.rng = model, rng
        self.current = VertexConditionalState(model, 0, initial=frozen_array(validate_state(initial, model.dimension)))

    def next_measurement_probabilities(self):
        return self.current.born_vertices()

    def step(self, outcome=None):
        if self.current.step:
            labels, probabilities = self.model.transitions(self.current.outcome)
            labels = tuple(int(x) for x in labels)
        else:
            labels, probabilities = self.model.graph.vertices, self.current.born_vertices()
        if outcome is None:
            i = int(self.rng.choice(len(labels), p=probabilities))
            outcome = labels[i]
        else:
            if not isinstance(outcome, Integral) or isinstance(outcome, bool) or outcome not in labels:
                raise ValueError("Unknown or zero-probability next vertex label.")
            i = labels.index(outcome)
        p = float(probabilities[i])
        if p <= 0:
            raise ValueError("Cannot condition on a zero-probability outcome.")
        self.current = VertexConditionalState(self.model, self.current.step + 1, int(outcome), p,
            self.current.log_path_probability + float(np.log(p)))
        return self.current


@dataclass(frozen=True)
class CompactVertexTrajectory:
    states: tuple[VertexConditionalState, ...]

    @property
    def outcomes(self):
        return tuple(s.outcome for s in self.states[1:])

    @property
    def log_path_probability(self):
        return self.states[-1].log_path_probability


class OptimizedVertexTrajectory:
    def __init__(self, walk, seed=None, **contract):
        self.model = walk if isinstance(walk, VertexReduction) and not contract else VertexReduction(walk, **contract)
        self.rng = np.random.default_rng(seed)

    def start(self, initial):
        return VertexSession(self.model, initial, self.rng)

    def run(self, initial, steps):
        count = validate_steps(steps)
        session = self.start(initial)
        states = [session.current]
        for _ in range(count): states.append(session.step())
        return CompactVertexTrajectory(tuple(states))
