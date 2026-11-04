"""General projective-measurement reference quantum trajectories."""

from dataclasses import dataclass
from typing import Protocol

import numpy as np
from numpy.typing import ArrayLike, NDArray

from .states import ComplexArray, checked_probabilities, validate_state, validate_steps
from .walk import ScatteringWalk


@dataclass(frozen=True)
class Trajectory:
    """Recorded time convention (Joye Section 4.2).

    states[n] is the state after n scattering steps; states[0] is initial.
    probabilities[n] is the law of X_(n+1), measured on states[n].
    outcomes[n] is X_(n+1). reduced_states[n] is the normalized state
    immediately after this measurement and before the unitary scattering.
    selected_probabilities[n] = probabilities[n][index(outcomes[n])].

    Pure input retains vector states; mixed input retains density matrices.
    """

    states: tuple[ComplexArray, ...]
    outcomes: tuple[int, ...]
    probabilities: tuple[NDArray[np.float64], ...]
    selected_probabilities: tuple[float, ...]
    reduced_states: tuple[ComplexArray, ...]

    @property
    def log_path_probability(self) -> float:
        return float(np.log(self.selected_probabilities).sum()) if self.selected_probabilities else 0.0


class TrajectoryEngine(Protocol):
    """Alternative samplers must preserve this record and time convention."""

    def run(self, initial: ArrayLike, steps: int) -> Trajectory: ...


class ReferenceTrajectory:
    """Measure incoming vertex, reduce, normalize, then scatter.

    The RNG is private to this engine. Identical initial state, walk, seed,
    and call sequence reproduce the trajectory. Repeated run calls advance
    the stream; create a new engine with the seed to replay an experiment.
    No pure-state or Markov reduction is assumed for mixed input.
    """

    def __init__(self, walk: ScatteringWalk, seed: int | None = None):
        self.walk = walk
        self.rng = np.random.default_rng(seed)

    def run(self, initial: ArrayLike, steps: int) -> Trajectory:
        count = validate_steps(steps)
        state = validate_state(initial, self.walk.graph.dimension)
        pure = state.ndim == 1
        states = [state]
        outcomes: list[int] = []
        probabilities: list[NDArray[np.float64]] = []
        selected_probabilities: list[float] = []
        reduced_states: list[ComplexArray] = []
        unitary = self.walk.operator
        incoming = [self.walk.graph.incoming_indices(x) for x in self.walk.graph.vertices]
        for _ in range(count):
            edge_weights = np.abs(state) ** 2 if pure else np.diag(state).real
            raw = np.array([edge_weights[indices].sum() for indices in incoming])
            born = checked_probabilities(raw)
            selected = int(self.rng.choice(len(incoming), p=born))
            indices = incoming[selected]
            # Divide by the actual projected norm/trace, not the roundoff-
            # adjusted sampler probabilities. Zero-weight events are never drawn.
            mass = float(raw[selected])
            if mass <= 0:
                raise ArithmeticError("A zero-probability measurement outcome was selected.")
            reduced = np.zeros_like(state)
            if pure:
                reduced[indices] = state[indices] / np.sqrt(mass)
                state = np.asarray(unitary @ reduced)
            else:
                reduced[np.ix_(indices, indices)] = state[np.ix_(indices, indices)] / mass
                left = unitary @ reduced
                state = np.asarray((unitary @ left.conj().T).conj().T)
            outcomes.append(self.walk.graph.vertices[selected])
            probabilities.append(born)
            selected_probabilities.append(float(born[selected]))
            reduced_states.append(reduced)
            states.append(state)
        return Trajectory(tuple(states), tuple(outcomes), tuple(probabilities), tuple(selected_probabilities), tuple(reduced_states))


class ReferenceVertexTrajectory:
    """Independent full Kraus-vector/density reference for the vertex model.

    V-02 is verified against these actual matrix products; this algorithm does
    not sample a cached P or replace its conditional state by an atom label.
    """

    def __init__(self, walk, seed=None):
        from .vertex import InducedVertexWalk
        if not isinstance(walk, InducedVertexWalk):
            raise ValueError("Expected an InducedVertexWalk.")
        self.walk, self.rng = walk, np.random.default_rng(seed)

    def run(self, initial, steps):
        count = validate_steps(steps)
        state = validate_state(initial, self.walk.dimension)
        states, outcomes, probabilities, selected, reduced_states = [state], [], [], [], []
        operators = self.walk.kraus_operators()
        for _ in range(count):
            pure = state.ndim == 1
            raw = abs(state) ** 2 if pure else np.diag(state).real
            born = checked_probabilities(raw)
            i = int(self.rng.choice(self.walk.dimension, p=born))
            reduced = np.zeros_like(state)
            if pure:
                reduced[i] = state[i] / np.sqrt(raw[i])
                state = operators[i] @ state / np.sqrt(raw[i])
            else:
                reduced[i, i] = 1
                state = operators[i] @ state @ operators[i].conj().T / raw[i]
            states.append(state); outcomes.append(self.walk.graph.vertices[i])
            probabilities.append(born); selected.append(float(born[i])); reduced_states.append(reduced)
        return Trajectory(tuple(states), tuple(outcomes), tuple(probabilities), tuple(selected), tuple(reduced_states))
