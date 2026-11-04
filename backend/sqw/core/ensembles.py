"""Bounded-memory independent trajectory ensembles (E-03/E-05, V-02/V-04).

Empirical preparation-label laws are kept separate from empirical Born laws.
The latter average conditional quantum-state probabilities: they are not extra
measurements and must not be confused with counts of past outcomes.
"""

from dataclasses import dataclass

import numpy as np

from .edge_markov import EdgeReduction
from .vertex_markov import VertexReduction
from .walk import ScatteringWalk
from .vertex import InducedVertexWalk
from .trajectories import ReferenceTrajectory, ReferenceVertexTrajectory
from .states import checked_probabilities, validate_state, validate_steps


@dataclass(frozen=True)
class EnsembleFrame:
    step: int
    state_counts: np.ndarray | None
    outcome_counts: np.ndarray | None
    empirical_born_vertices: np.ndarray | None
    empirical_born_edges: np.ndarray | None
    exact_state_weights: np.ndarray | None
    exact_born_vertices: np.ndarray | None
    exact_born_edges: np.ndarray | None
    state_total_variation: float | None
    born_vertex_total_variation: float | None


@dataclass(frozen=True)
class EnsembleResult:
    model: str
    strategy: str
    trajectories: int
    seed: int | None
    frames: tuple[EnsembleFrame, ...]
    selected_outcomes: tuple[tuple[int, ...], ...]
    selected_state_ids: tuple[tuple[int | None, ...], ...]


def _sample_groups(ids, transitions, rng):
    """One draw per path, from its OLD state; never update a path twice."""
    result = np.empty_like(ids)
    for label in np.unique(ids):
        positions = np.flatnonzero(ids == label)
        targets, p = transitions[int(label)]
        cdf = np.cumsum(p)
        cdf[-1] = 1.0
        choices = np.searchsorted(cdf, rng.random(len(positions)), side="right")
        result[positions] = targets[choices]
    return result


def run_ensemble(walk, initial, trajectories, steps, *, seed=None, strategy="optimized",
                 statistics=("states", "vertices", "edges", "exact"), selected_histories=0):
    """Stream reference paths or vectorize compact IDs, retaining only counts.

    statistics selects states/vertices/edges/exact; vertex models have no edge
    Born law (that output is None). selected_histories is a number of individual
    records to retain. Full density matrices are never kept across trajectories.
    State IDs are edge basis indices or vertex indices in the explicit basis;
    None marks warmstart stages before the fixed atom family is guaranteed.
    """
    count, horizon = validate_steps(trajectories), validate_steps(steps)
    keep = validate_steps(selected_histories)
    if count == 0:
        raise ValueError("An ensemble needs at least one trajectory.")
    if keep > count:
        raise ValueError("selected_histories cannot exceed trajectories.")
    requested = set(statistics)
    if not requested <= {"states", "vertices", "edges", "exact"}:
        raise ValueError("Unknown ensemble statistic.")
    if strategy not in {"reference", "optimized"}:
        raise ValueError("Strategy must be reference or optimized.")
    edge = isinstance(walk, ScatteringWalk)
    if not edge and not isinstance(walk, InducedVertexWalk):
        raise ValueError("Expected an edge or induced vertex walk.")
    model = EdgeReduction(walk) if edge else VertexReduction(walk)
    dimension, vertices = model.dimension, model.graph.vertices
    initial = validate_state(initial, dimension)
    m = len(vertices)
    rng = np.random.default_rng(seed)
    atom_start = 2 if edge else 1
    target_indices = np.array([model.graph.vertex_index[x] for x, _ in model.graph.directed_edges]) if edge else None
    want_states = "states" in requested
    want_born = bool(requested & {"vertices", "edges"})
    # Accumulate only requested outputs. Count arrays do not scale with N.
    states = np.zeros((horizon + 1, dimension), dtype=np.int64) if want_states else None
    outcomes = np.zeros((horizon + 1, m), dtype=np.int64) if want_states else None
    born = np.zeros((horizon + 1, dimension)) if want_born else None
    selected = np.empty((keep, horizon), dtype=np.int64)
    selected_ids = np.full((keep, horizon + 1), -1, dtype=np.int64)

    if strategy == "reference":
        engine_type = ReferenceTrajectory if edge else ReferenceVertexTrajectory
        for trajectory in range(count):
            child_seed = int(rng.integers(0, 2**63, dtype=np.int64))
            path = engine_type(walk, seed=child_seed).run(initial, horizon)
            for n, quantum in enumerate(path.states):
                if born is not None:
                    born[n] += (abs(quantum) ** 2 if quantum.ndim == 1 else np.diag(quantum).real) / count
                if n:
                    label = path.outcomes[n - 1]
                    if outcomes is not None: outcomes[n, model.graph.vertex_index[label]] += 1
                    if trajectory < keep: selected[trajectory, n - 1] = label
                if n >= atom_start:
                    atom = model.graph.edge_index[(path.outcomes[n - 1], path.outcomes[n - 2])] if edge else model.graph.vertex_index[path.outcomes[n - 1]]
                    if states is not None: states[n, atom] += 1
                    if trajectory < keep: selected_ids[trajectory, n] = atom
    else:
        diagonal = checked_probabilities(abs(initial) ** 2 if initial.ndim == 1 else np.diag(initial).real)
        if born is not None: born[0] = diagonal
        if horizon:
            p1 = model.vertex_marginal(diagonal) if edge else diagonal
            labels = rng.choice(m, size=count, p=checked_probabilities(p1))
            first_counts = np.bincount(labels, minlength=m)
            if outcomes is not None: outcomes[1] = first_counts
            if keep: selected[:, 0] = np.asarray(vertices)[labels[:keep]]
            if edge:
                blocks = model._first_blocks(initial)
                warm = {}
                for i, y in enumerate(vertices):
                    if p1[i] > 0:
                        local = checked_probabilities(np.diag(blocks[y]).real / p1[i])
                        warm[i] = (model.outgoing[y], local)
                        if born is not None:
                            born[1, model.outgoing[y]] = first_counts[i] / count * local
                if horizon >= 2:
                    ids = _sample_groups(labels, warm, rng)
                    transitions = {i: model.transitions(i) for i in range(dimension)}
            else:
                ids = labels
                transitions = {}
                for i, x in enumerate(vertices):
                    destinations, p = model.transitions(x)
                    transitions[i] = (np.array([model.graph.vertex_index[z] for z in destinations]), p)
            for n in range(atom_start, horizon + 1):
                if n > atom_start: ids = _sample_groups(ids, transitions, rng)
                hist = np.bincount(ids, minlength=dimension)
                if states is not None: states[n] = hist
                if born is not None:
                    born[n] = model.apply_M(hist / count) if edge else model.apply_P(hist / count)
                if edge:
                    labels = target_indices[ids]
                else:
                    labels = ids
                if outcomes is not None: outcomes[n] = np.bincount(labels, minlength=m)
                if keep:
                    selected[:, n - 1] = np.asarray(vertices)[labels[:keep]]
                    selected_ids[:, n] = ids[:keep]

    exact = model.iter_mean(initial, horizon) if "exact" in requested else iter([None] * (horizon + 1))
    frames = []
    for n, mean in enumerate(exact):
        empirical_edges = born[n].copy() if edge and born is not None and "edges" in requested else None
        empirical_vertices = (model.vertex_marginal(born[n]) if edge else born[n].copy()) if born is not None and "vertices" in requested else None
        exact_weights = None if mean is None else (mean.atom_weights if edge else mean.label_weights)
        exact_vertices = None if mean is None or "vertices" not in requested else mean.born_vertices()
        exact_edges = mean.born_edges() if mean is not None and edge and "edges" in requested else None
        state_tv = float(np.abs(states[n] / count - exact_weights).sum() / 2) if states is not None and exact_weights is not None else None
        vertex_tv = float(np.abs(empirical_vertices - exact_vertices).sum() / 2) if empirical_vertices is not None and exact_vertices is not None else None
        frames.append(EnsembleFrame(n, states[n].copy() if states is not None and n >= atom_start else None,
            outcomes[n].copy() if outcomes is not None and n else None, empirical_vertices, empirical_edges,
            exact_weights if want_states else None, exact_vertices, exact_edges, state_tv, vertex_tv))
    return EnsembleResult("edge" if edge else "vertex", strategy, count, seed, tuple(frames),
        tuple(tuple(int(x) for x in path) for path in selected),
        tuple(tuple(None if x < 0 else int(x) for x in path) for path in selected_ids))
