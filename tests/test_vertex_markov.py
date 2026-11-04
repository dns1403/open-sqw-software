"""V-01--V-06, T34 and AUD-01/02/05: independent Kraus comparisons."""

from itertools import product
from copy import deepcopy

import numpy as np
import pytest
from numpy.testing import assert_allclose

from sqw.core import (
    GraphModel, ScatteringWalk, InducedVertexWalk, VertexReduction,
    OptimizedVertexTrajectory, ReferenceVertexTrajectory, scattering_matrix,
)
from test_edge_markov import CASES, make_walk, initial_state, as_density


def vertex_fixture(kind, size, preset):
    edge = make_walk(kind, size, preset)
    rng = np.random.default_rng(18)
    omega = {}
    for x in edge.graph.vertices:
        w = rng.normal(size=edge.graph.degree(x)) + 1j * rng.normal(size=edge.graph.degree(x))
        omega[x] = w / np.linalg.norm(w)
    return InducedVertexWalk(edge, omega, {x: .3 * x - .8 for x in edge.graph.vertices})


@pytest.mark.parametrize("kind,size,preset", CASES)
@pytest.mark.parametrize("mixed", [False, True])
def test_V02_V04_sparse_means_timing_and_observables(kind, size, preset, mixed):
    walk = vertex_fixture(kind, size, preset)
    model = VertexReduction(walk)
    initial = initial_state(model.dimension, mixed)
    rho = as_density(initial)
    p = walk.markov_matrix
    assert_allclose(model.transition_matrix(), p, atol=1e-14, rtol=0)
    assert model.sparse_P.nnz <= model.dimension + walk.graph.dimension
    assert_allclose(p.sum(axis=1), 1, atol=2e-12, rtol=0)
    q1 = np.diag(rho).real
    observable = initial_state(model.dimension, True)
    atom_values = model.atom_expectations(observable)
    gs = walk.kraus_operators()
    for state in model.iter_mean(initial, 8):
        assert_allclose(state.density(), rho, atol=3e-12, rtol=0)
        assert_allclose(state.born_vertices(), np.diag(rho).real, atol=3e-12, rtol=0)
        assert_allclose(state.purity(), np.trace(rho @ rho).real, atol=3e-12, rtol=0)
        if state.step:
            expected = q1 @ np.linalg.matrix_power(p, state.step - 1)
            assert_allclose(state.label_weights, expected, atol=3e-12, rtol=0)
            assert_allclose(state.born_vertices(), expected @ p, atol=3e-12, rtol=0)
            assert_allclose(state.label_weights @ atom_values, np.trace(rho @ observable).real, atol=3e-12, rtol=0)
        rho = sum(g @ rho @ g.conj().T for g in gs)
        assert_allclose(np.trace(rho), 1, atol=3e-12, rtol=0)
        assert np.linalg.eigvalsh(rho).min() > -3e-12


@pytest.mark.parametrize("mixed", [False, True])
def test_V02_full_conditional_words_and_initial_coherences(mixed):
    walk = vertex_fixture("cycle", 3, "random")
    initial = initial_state(3, mixed)
    rho0 = as_density(initial)
    model = VertexReduction(walk)
    gs = walk.kraus_operators()
    for record in product(range(3), repeat=3):
        session = OptimizedVertexTrajectory(model).start(initial)
        raw = rho0
        for x in record:
            raw = gs[x] @ raw @ gs[x].conj().T
            mass = np.trace(raw).real
            if mass < 1e-28: break
            state = session.step(x)
            assert_allclose(state.density(), raw / mass, atol=2e-12, rtol=0)
            assert_allclose(np.exp(state.log_path_probability), mass, atol=2e-12, rtol=0)
            assert state.initial is None
            assert state.purity() == 1
            assert_allclose(state.reduced_density(), np.diag(np.eye(3)[x]), atol=1e-14)
    with_coherence = list(model.iter_mean(initial, 4))
    without = list(model.iter_mean(np.diag(np.diag(rho0)), 4))
    for a, b in zip(with_coherence[1:], without[1:]):
        assert_allclose(a.density(), b.density(), atol=1e-14)


def test_V06_beta_reuses_P_but_changes_quantum_state_and_observables():
    edge = make_walk("path", 3, "grover")
    reference = InducedVertexWalk(edge)
    model = VertexReduction(reference)
    beta = {0: np.pi / 2, 1: .7, 2: -.4}
    changed = model.with_beta(beta)
    expected = InducedVertexWalk(edge, beta=beta)
    assert changed._p is model._p
    assert_allclose(changed.transition_matrix(), model.transition_matrix(), atol=0, rtol=0)
    for x in range(3): assert_allclose(changed.atom_ket(x), expected.chi[x], atol=1e-14)
    assert not np.allclose(model.atom_density(0), changed.atom_density(0))
    q = np.array([1., 0, 0])
    observable = np.array([[0, 1, 0], [1, 0, 0], [0, 0, 0]])
    assert abs(q @ changed.atom_expectations(observable) - q @ model.atom_expectations(observable)) > .9
    # T33: bistochastic P is not sufficient for a unital channel.
    two = InducedVertexWalk(make_walk("path", 2, "identity"))
    assert_allclose(two.apply_channel(np.eye(2)), np.eye(2))
    chi = np.array([[1, 1], [1, np.exp(.5j)]]) / np.sqrt(2)
    assert_allclose((abs(chi) ** 2).sum(axis=1), 1)
    assert np.linalg.norm(chi @ chi.conj().T - np.eye(2)) > .1


def test_T34_stable_completion_alpha_invariance_without_tolerance_increase():
    graph = GraphModel.preset("path", 3)
    preparations = []
    for alpha in [0., .7, np.pi]:
        coins = {}
        for x in graph.vertices:
            w = np.ones(graph.degree(x)) / np.sqrt(graph.degree(x))
            q = np.outer(w, w)
            coins[x] = q + np.exp(1j * alpha) * (np.eye(len(w)) - q)
        vertex = InducedVertexWalk(ScatteringWalk(graph, coins), beta={0: .1, 1: .2, 2: .3})
        preparations.append(np.column_stack(list(vertex.chi.values())))
        assert vertex.chi[1][1] == 0  # leaf-boundary complements are exactly zero
    for chi in preparations:
        assert_allclose(chi, preparations[0], atol=1e-14, rtol=0)


def test_V01_tiny_genuine_completion_is_preserved_not_thresholded():
    graph = GraphModel.preset("path", 4)
    edge = ScatteringWalk(graph, {x: np.eye(graph.degree(x)) for x in graph.vertices})
    epsilon = 1e-12
    omega = {0: [1], 1: [0, 1], 2: [np.sqrt(1 - epsilon**2), epsilon], 3: [1]}
    vertex = InducedVertexWalk(edge, omega)
    assert_allclose(vertex.chi[1][1], epsilon, atol=1e-25, rtol=0)
    # AUD-02: four-vertex raw compression can be trace preserving.
    paired = InducedVertexWalk(edge, {0: [1], 1: [1, 0], 2: [0, 1], 3: [1]})
    for x in graph.vertices:
        assert_allclose(paired.theta[x], paired.chi[x], atol=0, rtol=0)
        assert_allclose(np.vdot(paired.theta[x], paired.theta[x]), 1)


def test_AUD01_transient_mass_and_period_two_are_retained():
    # With fixed ascending port order the DFT path sends the transient tail
    # into the first two-vertex recurrent class; none of its mass is dropped.
    model = VertexReduction(InducedVertexWalk(make_walk("path", 5, "dft")))
    rho0 = np.diag([0, 0, 0, 0, 1])
    last = list(model.iter_mean(rho0, 200))[-1]
    assert_allclose(last.born_vertices(), [2/3, 1/3, 0, 0, 0], atol=2e-12, rtol=0)
    periodic = VertexReduction(InducedVertexWalk(make_walk("path", 2, "identity")))
    path = OptimizedVertexTrajectory(periodic, seed=7).run([1, 0], 6)
    assert path.outcomes == (0, 1, 0, 1, 0, 1)


def test_vertex_online_reproducibility_reference_and_lazy_state():
    walk = vertex_fixture("star", 5, "random")
    initial = initial_state(5, True)
    engine = OptimizedVertexTrajectory(walk, seed=61)
    rng0 = deepcopy(engine.rng.bit_generator.state)
    session = engine.start(initial)
    session.next_measurement_probabilities(); session.current.density()
    assert engine.rng.bit_generator.state == rng0
    online = tuple(session.step().outcome for _ in range(20))
    batch = OptimizedVertexTrajectory(walk, seed=61).run(initial, 20)
    assert batch.outcomes == online
    # No identical-seed equivalence assertion across distinct samplers.
    reference = ReferenceVertexTrajectory(walk, seed=73).run(initial, 8)
    forced = OptimizedVertexTrajectory(walk).start(initial)
    for i, x in enumerate(reference.outcomes, 1):
        assert_allclose(forced.step(x).density(), reference.states[i], atol=2e-12, rtol=0)
    assert_allclose(forced.current.log_path_probability, reference.log_path_probability, atol=2e-12)


def test_vertex_eligibility_and_invalid_inputs():
    walk = vertex_fixture("path", 3, "dft")
    for options in ({"fully_observed": False}, {"time_dependent": True}, {"instrument": "different"}):
        with pytest.raises(ValueError): OptimizedVertexTrajectory(walk, **options)
    model = VertexReduction(walk)
    with pytest.raises(ValueError): model.apply_P([1, 0])
    with pytest.raises(ValueError): model.with_beta({0: 0})
    with pytest.raises(ValueError): model.with_beta({0: 0, 1: np.nan, 2: 0})
    with pytest.raises(ValueError): model.atom_ket(True)
    with pytest.raises(ValueError): model.transition_matrix(max_dimension=2)
