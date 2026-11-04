"""Ensemble laws are not extra outcome measurements or individual densities."""
import numpy as np
import pytest
from numpy.testing import assert_allclose

from sqw.core import run_ensemble, InducedVertexWalk, EdgeReduction, VertexReduction
from test_edge_markov import make_walk, initial_state


@pytest.mark.parametrize("vertex", [False, True])
@pytest.mark.parametrize("strategy", ["reference", "optimized"])
def test_ensemble_sampling_matches_independent_mean_with_statistical_bound(vertex, strategy):
    walk = make_walk("cycle", 3, "random")
    if vertex: walk = InducedVertexWalk(walk, beta={0: .4, 1: -.7, 2: .9})
    dimension = 3 if vertex else 6
    initial = initial_state(dimension, True)
    result = run_ensemble(walk, initial, 3000, 4, seed=7, strategy=strategy, selected_histories=2)
    rho = initial
    kraus = walk.kraus_operators()
    for frame in result.frames:
        expected = np.diag(rho).real
        exact = frame.exact_born_vertices if vertex else frame.exact_born_edges
        empirical = frame.empirical_born_vertices if vertex else frame.empirical_born_edges
        assert_allclose(exact, expected, atol=2e-12, rtol=0)
        # Independent paths; bounded variables. Conservative deterministic
        # seeded check (~7 marginal standard deviations), not exact equality.
        assert_allclose(empirical, expected, atol=.065, rtol=0)
        if frame.state_counts is not None:
            assert frame.state_counts.sum() == 3000
            assert frame.state_total_variation < .09
            assert_allclose(frame.exact_state_weights.sum(), 1, atol=1e-12)
        if frame.outcome_counts is not None: assert frame.outcome_counts.sum() == 3000
        assert_allclose(frame.empirical_born_vertices.sum(), 1, atol=1e-12)
        rho = sum(k @ rho @ k.conj().T for k in kraus)
    assert len(result.selected_outcomes) == 2
    assert len(result.selected_outcomes[0]) == 4
    assert result.selected_state_ids[0][0] is None
    if not vertex: assert result.selected_state_ids[0][1] is None


@pytest.mark.parametrize("vertex", [False, True])
def test_compact_selected_histories_reproducibility_and_state_born_timing(vertex):
    walk = make_walk("path", 3, "hadamard")
    if vertex: walk = InducedVertexWalk(walk)
    model = VertexReduction(walk) if vertex else EdgeReduction(walk)
    initial = initial_state(model.dimension, False)
    kwargs = dict(seed=17, selected_histories=5)
    a = run_ensemble(walk, initial, 20000, 20, **kwargs)
    b = run_ensemble(walk, initial, 20000, 20, **kwargs)
    assert a.selected_outcomes == b.selected_outcomes
    for f, other in zip(a.frames, b.frames):
        if f.state_counts is not None:
            assert_allclose(f.state_counts, other.state_counts, atol=0, rtol=0)
            prepared = f.state_counts / a.trajectories
            born = model.apply_P(prepared) if vertex else model.apply_M(prepared)
            assert_allclose(born, f.empirical_born_vertices if vertex else f.empirical_born_edges, atol=1e-14)
    for outcomes, ids in zip(a.selected_outcomes, a.selected_state_ids):
        for n in range(1 if vertex else 2, 21):
            label = model.graph.vertices[ids[n]] if vertex else model.graph.directed_edges[ids[n]]
            assert label == (outcomes[n - 1] if vertex else (outcomes[n - 1], outcomes[n - 2]))


@pytest.mark.parametrize("vertex", [False, True])
@pytest.mark.parametrize("steps", [0, 1, 2])
def test_output_selection_and_warmstart_only_ensembles(vertex, steps):
    walk = make_walk("cycle", 3, "dft")
    if vertex: walk = InducedVertexWalk(walk)
    d = 3 if vertex else 6
    result = run_ensemble(walk, initial_state(d, True), 1, steps, seed=42,
                          statistics=("vertices",), selected_histories=1)
    assert len(result.frames) == steps + 1
    assert len(result.selected_outcomes[0]) == steps
    for frame in result.frames:
        assert frame.state_counts is None
        assert frame.exact_state_weights is None
        assert frame.exact_born_vertices is None
        assert frame.empirical_born_edges is None
        assert frame.empirical_born_vertices.sum() == pytest.approx(1)


def test_ensemble_zero_probabilities_do_not_create_impossible_records():
    walk = make_walk("path", 3, "identity")
    initial = np.zeros(4); initial[0] = 1
    result = run_ensemble(walk, initial, 10000, 8, seed=11, selected_histories=2)
    assert result.selected_outcomes == ((0, 1) * 4,) * 2
    for frame in result.frames:
        assert frame.born_vertex_total_variation == 0


def test_ensemble_validation():
    walk = make_walk("path", 3, "identity")
    initial = np.ones(4) / 2
    for args in ({"trajectories": 0}, {"steps": -1}, {"strategy": "guess"},
                 {"statistics": ("wrong",)}, {"selected_histories": 11}):
        kwargs = {"trajectories": 10, "steps": 3, **args}
        with pytest.raises(ValueError): run_ensemble(walk, initial, **kwargs)
