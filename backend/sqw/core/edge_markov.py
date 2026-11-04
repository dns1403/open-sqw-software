"""Exact SIMPLE_STATIC edge reduction: handoff E-02--E-05.

Arcs are (target, source). M is column stochastic: q_next = M @ q.
An atom ID e labels U|e>, never the basis ket |e>. References use the
independent ScatteringWalk channel and ReferenceTrajectory, not this module.
"""

from dataclasses import dataclass, field
from numbers import Integral

import numpy as np
from numpy.typing import ArrayLike, NDArray
from scipy.sparse import csr_matrix

from .graph import GraphModel
from .states import (
    ComplexArray, checked_probabilities, complex_array, validate_state, validate_steps,
)
from .walk import ScatteringWalk
from .structural_support import edge_support


def frozen_array(value):
    result = np.array(value, copy=True)
    result.setflags(write=False)
    return result


def density_of(state):
    return np.outer(state, state.conj()) if state.ndim == 1 else state.copy()


@dataclass(frozen=True)
class Eligibility:
    eligible: bool
    reasons: tuple[str, ...] = ()

    def require(self):
        if not self.eligible:
            raise ValueError("Optimized strategy is ineligible: " + "; ".join(self.reasons))


def edge_eligibility(walk, *, instrument="incoming_vertex_before_scattering",
                     fully_observed=True, time_dependent=False) -> Eligibility:
    """E-02/NEW-03: do not infer guarantees for arbitrary instrument subclasses.

    GraphModel validates finite, simple, undirected, connected, loopless graphs.
    ScatteringWalk validates static unitaries. Unsupported graphs/instruments
    are rejected explicitly; the current reference also requires GraphModel.
    """
    reasons = []
    if type(walk) is not ScatteringWalk or type(getattr(walk, "graph", None)) is not GraphModel:
        reasons.append("requires the validated finite simple-graph ScatteringWalk")
    if instrument != "incoming_vertex_before_scattering":
        reasons.append("requires incoming-vertex measurement before scattering")
    if fully_observed is not True:
        reasons.append("requires every measurement outcome to be observed")
    if time_dependent is not False:
        reasons.append("requires time-independent scattering")
    return Eligibility(not reasons, tuple(reasons))


class EdgeReduction:
    """Local exact M multiplication, q2 initialization and lazy atom outputs.

    No dense global M or U is constructed here. Local complex matrices are
    copied once, retaining phases and insulating this static model from edits.
    """

    def __init__(self, walk: ScatteringWalk, **contract):
        self.eligibility = edge_eligibility(walk, **contract)
        self.eligibility.require()
        self.graph = walk.graph
        self.dimension = self.graph.dimension
        self.scattering = {x: frozen_array(walk.scattering[x]) for x in self.graph.vertices}
        self.incoming = {x: self.graph.incoming_indices(x) for x in self.graph.vertices}
        self.outgoing = {x: self.graph.outgoing_indices(x) for x in self.graph.vertices}
        self.local_probabilities = {x: frozen_array(abs(s) ** 2) for x, s in self.scattering.items()}
        self._ports = {x: {y: i for i, y in enumerate(self.graph.neighbors[x])} for x in self.graph.vertices}

    def _weights(self, weights):
        q = checked_probabilities(weights)
        if q.shape != (self.dimension,):
            raise ValueError(f"Edge atom weights must have length {self.dimension}.")
        return q

    def _atom(self, atom_id):
        if not isinstance(atom_id, Integral) or isinstance(atom_id, bool) or not 0 <= atom_id < self.dimension:
            raise ValueError("Edge atom ID must be a valid directed-edge basis index.")
        x, y = self.graph.directed_edges[int(atom_id)]
        return x, self._ports[x][y]

    def apply_M(self, weights: ArrayLike) -> NDArray[np.float64]:
        """E-03: column convention, local |S(x)|² matvec and arc flip."""
        q = self._weights(weights)
        out = np.zeros(self.dimension)
        for x in self.graph.vertices:
            out[self.outgoing[x]] = self.local_probabilities[x] @ q[self.incoming[x]]
        return checked_probabilities(out)

    def transition_matrix(self, *, max_dimension=512):
        """Explicit small-graph diagnostic M; never needed for evolution."""
        if self.dimension > max_dimension:
            raise ValueError("Dense edge transition diagnostic exceeds max_dimension.")
        matrix = np.zeros((self.dimension, self.dimension))
        for x in self.graph.vertices:
            matrix[np.ix_(self.outgoing[x], self.incoming[x])] = self.local_probabilities[x]
        return matrix

    @property
    def sparse_M(self):
        """Sparse column-stochastic M, assembled from local blocks only."""
        rows, cols, data = [], [], []
        for x, block in self.local_probabilities.items():
            r, c = np.nonzero(block)
            rows.extend(self.outgoing[x][r]); cols.extend(self.incoming[x][c]); data.extend(block[r, c])
        return csr_matrix((data, (rows, cols)), shape=(self.dimension, self.dimension))

    @property
    def analytic_support(self):
        return edge_support(self.graph, self.scattering)

    def transitions(self, atom_id):
        """Next atom IDs and their probabilities, in stored neighbor order."""
        x, port = self._atom(atom_id)
        return self.outgoing[x].copy(), checked_probabilities(self.local_probabilities[x][:, port])

    def atom_ket(self, atom_id) -> ComplexArray:
        x, port = self._atom(atom_id)
        ket = np.zeros(self.dimension, dtype=complex)
        ket[self.outgoing[x]] = self.scattering[x][:, port]
        return ket

    def atom_density(self, atom_id) -> ComplexArray:
        return density_of(self.atom_ket(atom_id))

    def atom_born_edges(self, atom_id):
        x, port = self._atom(atom_id)
        out = np.zeros(self.dimension)
        out[self.outgoing[x]] = self.local_probabilities[x][:, port]
        return checked_probabilities(out)

    def vertex_marginal(self, edges):
        return np.array([np.sum(edges[self.incoming[x]]) for x in self.graph.vertices])

    def _first_blocks(self, state):
        """Unnormalized outgoing blocks of Phi(rho0), retaining coherence."""
        blocks = {}
        for x in self.graph.vertices:
            ids = self.incoming[x]
            s = self.scattering[x]
            if state.ndim == 1:
                local = s @ state[ids]
                block = np.outer(local, local.conj())
            else:
                block = s @ state[np.ix_(ids, ids)] @ s.conj().T
            blocks[x] = frozen_array(block)
        return blocks

    def prepare_q2(self, initial: ArrayLike):
        """E-03: joint Pr(X1=y, X2=x), not a diagonal-input approximation."""
        state = validate_state(initial, self.dimension)
        q = np.zeros(self.dimension)
        for x, block in self._first_blocks(state).items():
            q[self.outgoing[x]] = np.diag(block).real
        return checked_probabilities(q)

    def mean_density(self, weights: ArrayLike):
        """E-05: physical U diag(q) U†, allocated only on request."""
        q = self._weights(weights)
        out = np.zeros((self.dimension, self.dimension), dtype=complex)
        for x, s in self.scattering.items():
            out[np.ix_(self.outgoing[x], self.outgoing[x])] = (s * q[self.incoming[x]]) @ s.conj().T
        return out

    def atom_expectations(self, observable: ArrayLike):
        """E-05: <eta_e|A|eta_e>; keeps complex phase-sensitive observables."""
        a = complex_array(observable, "Observable")
        if a.shape != (self.dimension, self.dimension) or not np.allclose(a, a.conj().T, rtol=0, atol=1e-10):
            raise ValueError("Observable must be a Hermitian matrix in the directed-edge basis.")
        values = np.zeros(self.dimension)
        for x, s in self.scattering.items():
            block = a[np.ix_(self.outgoing[x], self.outgoing[x])]
            values[self.incoming[x]] = np.einsum('ij,ij->j', s.conj(), block @ s).real
        return values

    def iter_mean(self, initial, steps):
        """Yield t=0, exact local t=1, then atom laws q_n (not Born laws)."""
        count = validate_steps(steps)
        state = frozen_array(validate_state(initial, self.dimension))
        yield EdgeMeanState(self, 0, initial=state)
        if count == 0:
            return
        blocks = self._first_blocks(state)
        yield EdgeMeanState(self, 1, blocks=blocks)
        if count == 1:
            return
        q = np.zeros(self.dimension)
        for x, block in blocks.items():
            q[self.outgoing[x]] = np.diag(block).real
        q = checked_probabilities(q)
        for step in range(2, count + 1):
            yield EdgeMeanState(self, step, atom_weights=frozen_array(q))
            if step < count:
                q = self.apply_M(q)


@dataclass(frozen=True)
class EdgeMeanState:
    model: EdgeReduction = field(repr=False)
    step: int
    initial: ComplexArray | None = field(default=None, repr=False)
    blocks: dict | None = field(default=None, repr=False)
    atom_weights: NDArray[np.float64] | None = None

    def density(self):
        if self.step == 0:
            return density_of(self.initial)
        if self.atom_weights is not None:
            return self.model.mean_density(self.atom_weights)
        out = np.zeros((self.model.dimension, self.model.dimension), dtype=complex)
        for x, block in self.blocks.items():
            ids = self.model.outgoing[x]
            out[np.ix_(ids, ids)] = block
        return out

    def born_edges(self):
        """E-05: at n>=2 this is M q_n, with the extra step intentional."""
        if self.atom_weights is not None:
            return self.model.apply_M(self.atom_weights)
        if self.step == 0:
            return checked_probabilities(abs(self.initial) ** 2 if self.initial.ndim == 1 else np.diag(self.initial).real)
        out = np.zeros(self.model.dimension)
        for x, block in self.blocks.items():
            out[self.model.outgoing[x]] = np.diag(block).real
        return checked_probabilities(out)

    def born_vertices(self):
        return self.model.vertex_marginal(self.born_edges())

    def purity(self):
        if self.atom_weights is not None:
            return float(self.atom_weights @ self.atom_weights)
        if self.step == 1:
            return float(sum(np.vdot(b, b).real for b in self.blocks.values()))
        return 1.0 if self.initial.ndim == 1 else float(np.vdot(self.initial, self.initial).real)


@dataclass(frozen=True)
class EdgeConditionalState:
    """Stage-specific conditional state. After t=2 only an atom ID is stored.

    local at t=1 is the normalized post-scattering outgoing vector/block.
    Arrays are readonly, and reconstruction methods return detached arrays.
    """

    model: EdgeReduction = field(repr=False)
    step: int
    outcome: int | None = None
    selected_probability: float | None = None
    log_path_probability: float = 0.0
    atom_id: int | None = None
    initial: ComplexArray | None = field(default=None, repr=False)
    local: ComplexArray | None = field(default=None, repr=False)

    @property
    def stage(self):
        return "initial" if self.step == 0 else "first_scattering" if self.step == 1 else "edge_atom"

    def ket(self):
        if self.atom_id is not None:
            return self.model.atom_ket(self.atom_id)
        data = self.initial if self.step == 0 else self.local
        if data.ndim != 1:
            raise ValueError("A mixed warmstart has no stored pure-state ket; request density().")
        if self.step == 0:
            return data.copy()
        out = np.zeros(self.model.dimension, dtype=complex)
        out[self.model.outgoing[self.outcome]] = data
        return out

    def density(self):
        if self.atom_id is not None:
            return self.model.atom_density(self.atom_id)
        if self.step == 0:
            return density_of(self.initial)
        out = np.zeros((self.model.dimension, self.model.dimension), dtype=complex)
        ids = self.model.outgoing[self.outcome]
        out[np.ix_(ids, ids)] = density_of(self.local)
        return out

    def reduced_density(self):
        """State immediately after this measurement, BEFORE scattering."""
        if self.step == 0:
            raise ValueError("There has not yet been a measurement at step zero.")
        out = np.zeros((self.model.dimension, self.model.dimension), dtype=complex)
        if self.atom_id is not None:
            out[self.atom_id, self.atom_id] = 1
        else:
            s = self.model.scattering[self.outcome]
            local = s.conj().T @ density_of(self.local) @ s
            ids = self.model.incoming[self.outcome]
            out[np.ix_(ids, ids)] = local
        return out

    def born_edges(self):
        if self.atom_id is not None:
            return self.model.atom_born_edges(self.atom_id)
        data = self.initial if self.step == 0 else self.local
        values = abs(data) ** 2 if data.ndim == 1 else np.diag(data).real
        if self.step == 0:
            return checked_probabilities(values)
        out = np.zeros(self.model.dimension)
        out[self.model.outgoing[self.outcome]] = values
        return checked_probabilities(out)

    def born_vertices(self):
        return self.model.vertex_marginal(self.born_edges())

    def purity(self):
        if self.atom_id is not None:
            return 1.0
        data = self.initial if self.step == 0 else self.local
        return 1.0 if data.ndim == 1 else float(np.vdot(data, data).real)


class EdgeSession:
    """Sequential online E-03 warmstart. Constructing/inspecting draws nothing."""

    def __init__(self, model, initial, rng):
        self.model, self.rng = model, rng
        self.current = EdgeConditionalState(model, 0, initial=frozen_array(validate_state(initial, model.dimension)))

    def next_measurement_probabilities(self):
        return self.current.born_vertices()

    def step(self, outcome=None):
        """Sample exactly one outcome, or condition on a specified valid label.

        Explicit conditioning is useful for deterministic Kraus-word checks;
        it does not consume the random stream. Zero-mass branches are rejected.
        """
        current, model = self.current, self.model
        if current.step == 0:
            labels = model.graph.vertices
            raw = current.born_vertices()
        elif current.step == 1:
            labels = model.graph.neighbors[current.outcome]
            raw = abs(current.local) ** 2 if current.local.ndim == 1 else np.diag(current.local).real
        else:
            x, port = model._atom(current.atom_id)
            labels = model.graph.neighbors[x]
            raw = model.local_probabilities[x][:, port]
        probabilities = checked_probabilities(raw)
        if outcome is None:
            index = int(self.rng.choice(len(labels), p=probabilities))
            outcome = labels[index]
        else:
            if not isinstance(outcome, Integral) or isinstance(outcome, bool) or outcome not in labels:
                raise ValueError("Outcome is not a valid next vertex label.")
            index = labels.index(outcome)
        p = float(probabilities[index])
        if p <= 0:
            raise ValueError("Cannot condition on a zero-probability outcome.")
        log_p = current.log_path_probability + float(np.log(p))
        if current.step == 0:
            ids, s = model.incoming[outcome], model.scattering[outcome]
            state = current.initial
            if state.ndim == 1:
                block = state[ids]
                local = s @ block / np.linalg.norm(block)
            else:
                block = state[np.ix_(ids, ids)]
                local = s @ block @ s.conj().T / np.trace(block).real
            result = EdgeConditionalState(model, 1, int(outcome), p, log_p, local=frozen_array(local))
        else:
            atom = model.graph.edge_index[(int(outcome), current.outcome)]
            result = EdgeConditionalState(model, current.step + 1, int(outcome), p, log_p, atom_id=atom)
        self.current = result
        return result


@dataclass(frozen=True)
class CompactEdgeTrajectory:
    states: tuple[EdgeConditionalState, ...]

    @property
    def outcomes(self):
        return tuple(state.outcome for state in self.states[1:])

    @property
    def log_path_probability(self):
        return self.states[-1].log_path_probability


class OptimizedEdgeTrajectory:
    """E-02/E-03 exact edge-atom sampler; no future outcome is pre-sampled.

    start(initial) returns an online session. run() records only the initial
    state, first local state and compact later frames. RNG semantics match the
    reference: repeated calls advance the stream; a new seeded engine replays.
    Direct q2 initialization uses a different sampler with the SAME joint law,
    not necessarily the same seeded record as sequential initialization.
    """

    def __init__(self, walk, seed=None, **contract):
        self.model = walk if isinstance(walk, EdgeReduction) and not contract else EdgeReduction(walk, **contract)
        self.rng = np.random.default_rng(seed)

    def start(self, initial):
        return EdgeSession(self.model, initial, self.rng)

    def run(self, initial, steps, *, initialization="sequential"):
        count = validate_steps(steps)
        if initialization not in {"sequential", "direct"}:
            raise ValueError("Initialization must be sequential or direct.")
        session = self.start(initial)
        frames = [session.current]
        if initialization == "direct" and count >= 2:
            q2 = self.model.prepare_q2(initial)
            atom = int(self.rng.choice(self.model.dimension, p=q2))
            x, y = self.model.graph.directed_edges[atom]
            frames.extend((session.step(y), session.step(x)))
        while session.current.step < count:
            frames.append(session.step())
        return CompactEdgeTrajectory(tuple(frames))
