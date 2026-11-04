"""E-02--E-05 and AUD-03/04/05 against independent full Kraus words."""

from copy import deepcopy
from itertools import product

import networkx as nx
import numpy as np
import pytest
from numpy.testing import assert_allclose

from sqw.core import (
    EdgeReduction, GraphModel, OptimizedEdgeTrajectory, ScatteringWalk,
    density_from_state, edge_eligibility, scattering_matrix,
)


CASES = [("path", 3, "identity"), ("path", 3, "hadamard"),
         ("cycle", 3, "grover"), ("cycle", 3, "dft"), ("cycle", 3, "random"),
         ("star", 5, "random"), ("star", 5, "grover"), ("star", 5, "dft")]


def make_walk(kind, size, preset):
    graph = GraphModel.preset(kind, size)
    rng = np.random.default_rng(772)
    return ScatteringWalk(graph, {x: scattering_matrix(
        "identity" if preset == "hadamard" and graph.degree(x) != 2 else preset,
        graph.degree(x), rng) for x in graph.vertices})


def initial_state(dimension, mixed):
    rng = np.random.default_rng(56)
    a = rng.normal(size=(dimension, dimension)) + 1j * rng.normal(size=(dimension, dimension))
    if not mixed:
        return a[:, 0] / np.linalg.norm(a[:, 0])
    rho = a @ a.conj().T
    return rho / np.trace(rho)


def as_density(state):
    return density_from_state(state) if state.ndim == 1 else state


@pytest.mark.parametrize("kind,size,preset", CASES)
@pytest.mark.parametrize("mixed", [False, True])
def test_E03_E05_q2_means_observables_and_orientation(kind, size, preset, mixed):
    walk = make_walk(kind, size, preset)
    model = EdgeReduction(walk)
    initial = initial_state(model.dimension, mixed)
    rho = as_density(initial)
    kraus = walk.kraus_operators()
    # Dense Kraus sum, independent of optimized blocks and M.
    phi = lambda a: sum(k @ a @ k.conj().T for k in kraus)
    q2 = model.prepare_q2(initial)
    assert_allclose(q2, np.diag(phi(rho)).real, atol=2e-12, rtol=0)
    matrix = model.transition_matrix()
    u = walk.operator.toarray()
    assert_allclose(matrix, abs(u) ** 2, atol=2e-12, rtol=0)
    assert_allclose(matrix.sum(axis=0), 1, atol=2e-12, rtol=0)
    assert_allclose(matrix.sum(axis=1), 1, atol=2e-12, rtol=0)
    observable = initial_state(model.dimension, True)
    atom_values = model.atom_expectations(observable)
    for state in model.iter_mean(initial, 8):
        assert_allclose(state.density(), rho, atol=3e-12, rtol=0)
        assert_allclose(state.born_edges(), np.diag(rho).real, atol=3e-12, rtol=0)
        assert_allclose(state.born_vertices(), walk.vertex_probabilities(rho), atol=3e-12, rtol=0)
        assert_allclose(state.purity(), np.trace(rho @ rho).real, atol=3e-12, rtol=0)
        if state.step >= 2:
            q = np.linalg.matrix_power(matrix, state.step - 2) @ q2
            assert_allclose(state.atom_weights, q, atol=3e-12, rtol=0)
            assert_allclose(model.apply_M(q), matrix @ q, atol=3e-12, rtol=0)
            assert_allclose(q @ atom_values, np.trace(rho @ observable).real, atol=3e-12, rtol=0)
        assert_allclose(np.trace(rho), 1, atol=3e-12, rtol=0)
        assert np.linalg.eigvalsh(rho).min() > -3e-12
        rho = phi(rho)


@pytest.mark.parametrize("kind,size,preset", CASES)
@pytest.mark.parametrize("mixed", [False, True])
def test_E02_E03_AUD04_every_short_record_matches_full_kraus_word(kind, size, preset, mixed):
    walk = make_walk(kind, size, preset)
    initial = initial_state(walk.graph.dimension, mixed)
    rho0 = as_density(initial)
    engine = OptimizedEdgeTrajectory(walk, seed=19)
    ks = dict(zip(walk.graph.vertices, walk.kraus_operators()))
    for record in product(walk.graph.vertices, repeat=3):
        session = engine.start(initial)
        unnormalized = rho0.copy()
        for step, x in enumerate(record, 1):
            k = ks[x]
            unnormalized = k @ unnormalized @ k.conj().T
            mass = float(np.trace(unnormalized).real)
            if mass <= 1e-28:
                # Structural zeros are tested separately; tiny floating tails
                # in analytical zero fixtures are not declared impossible.
                break
            state = session.step(x)
            assert_allclose(np.exp(state.log_path_probability), mass, atol=3e-12, rtol=0)
            assert_allclose(state.density(), unnormalized / mass, atol=3e-12, rtol=0)
            projected = walk.incoming_projector(x) @ (rho0 if step == 1 else previous) @ walk.incoming_projector(x)
            projected /= np.trace(projected)
            assert_allclose(state.reduced_density(), projected, atol=3e-12, rtol=0)
            if step >= 2:
                assert state.initial is None and state.local is None
                assert walk.graph.directed_edges[state.atom_id] == (x, record[step - 2])
                assert_allclose(state.purity(), 1, atol=3e-12, rtol=0)
                assert_allclose(density_from_state(state.ket()), state.density(), atol=3e-12, rtol=0)
            previous = unnormalized / mass


def test_E03_coherence_changes_q2_and_atom_is_scattered_superposition():
    walk = make_walk("path", 3, "hadamard")
    model = EdgeReduction(walk)
    psi = np.zeros(4, complex)
    psi[walk.graph.incoming_indices(1)] = [1 / np.sqrt(2), 1 / np.sqrt(2)]
    other = psi.copy()
    other[walk.graph.incoming_indices(1)[1]] *= -1
    assert_allclose(abs(psi) ** 2, abs(other) ** 2)
    assert np.linalg.norm(model.prepare_q2(psi) - model.prepare_q2(other), ord=1) > 1.99
    atom = walk.graph.edge_index[(1, 0)]
    assert np.count_nonzero(abs(model.atom_ket(atom)) > .1) == 2
    assert_allclose(model.atom_ket(atom), walk.operator.toarray()[:, atom], atol=1e-14)
    uniform_mixed = np.eye(4) / 4
    session = OptimizedEdgeTrajectory(walk).start(uniform_mixed)
    one = session.step(1)
    assert one.purity() == pytest.approx(.5)
    assert session.step(0).purity() == 1


def test_E03_direct_pair_sampler_preserves_joint_law_without_extra_markov_step():
    walk = make_walk("cycle", 3, "random")
    initial = initial_state(6, True)
    model = EdgeReduction(walk)
    q2 = model.prepare_q2(initial)
    class PairChoice:
        def __init__(self, selected): self.selected, self.calls = selected, 0
        def choice(self, size, p):
            assert size == 6
            assert_allclose(p, q2, atol=1e-14)
            self.calls += 1
            return self.selected
    for e in range(6):
        engine = OptimizedEdgeTrajectory(model)
        engine.rng = sampler = PairChoice(e)
        path = engine.run(initial, 2, initialization="direct")
        x, y = walk.graph.directed_edges[e]
        assert path.outcomes == (y, x)
        assert path.states[-1].atom_id == e
        assert sampler.calls == 1
        assert_allclose(np.exp(path.log_path_probability), q2[e], atol=1e-14)


def test_online_step_zero_one_replay_and_lazy_queries_do_not_advance_rng():
    walk = make_walk("star", 5, "random")
    initial = initial_state(8, True)
    a = OptimizedEdgeTrajectory(walk, seed=19)
    rng0 = deepcopy(a.rng.bit_generator.state)
    session = a.start(initial)
    assert session.current.stage == "initial"
    assert a.rng.bit_generator.state == rng0
    assert len(a.run(initial, 0, initialization="direct").states) == 1
    assert a.rng.bit_generator.state == rng0
    one = session.step()
    rng1 = deepcopy(a.rng.bit_generator.state)
    assert rng1 != rng0
    one.density(); one.born_edges(); session.next_measurement_probabilities()
    assert a.rng.bit_generator.state == rng1
    online = [one.outcome]
    for _ in range(19): online.append(session.step().outcome)
    batch = OptimizedEdgeTrajectory(walk, seed=19).run(initial, 20)
    assert tuple(online) == batch.outcomes
    replay = OptimizedEdgeTrajectory(walk, seed=19).run(initial, 20)
    assert batch.outcomes == replay.outcomes
    assert_allclose(batch.states[-1].density(), replay.states[-1].density())
    only_one = OptimizedEdgeTrajectory(walk, seed=19).run(initial, 1, initialization="direct")
    assert only_one.outcomes == (one.outcome,)


def test_zero_probabilities_periodic_reducible_chains_and_noncontiguous_labels():
    graph = GraphModel.from_edges([10, 30, 90], [(10, 30), (30, 90)])
    walk = ScatteringWalk(graph, {x: np.eye(graph.degree(x)) for x in graph.vertices})
    psi = np.zeros(4, complex); psi[graph.edge_index[(10, 30)]] = 1
    session = OptimizedEdgeTrajectory(walk, seed=1).start(psi)
    with pytest.raises(ValueError, match="zero-probability"):
        session.step(90)
    path = OptimizedEdgeTrajectory(walk, seed=1).run(psi, 10)
    assert path.outcomes == (10, 30) * 5
    m = EdgeReduction(walk).transition_matrix()
    assert_allclose(m @ m, np.eye(4))
    assert np.count_nonzero(path.states[-1].born_edges()) == 1


def test_eligibility_rejects_unsupported_instruments_and_parallel_graphs():
    walk = make_walk("path", 3, "identity")
    assert edge_eligibility(walk).eligible
    for options in ({"fully_observed": False}, {"time_dependent": True}, {"instrument": "after_scattering"}):
        assert not edge_eligibility(walk, **options).eligible
        with pytest.raises(ValueError, match="ineligible"):
            OptimizedEdgeTrajectory(walk, **options)
    assert not edge_eligibility(nx.MultiGraph([(0, 1), (0, 1)])).eligible
    with pytest.raises(ValueError): GraphModel(nx.MultiGraph([(0, 1), (0, 1)]))


def test_invalid_states_weights_ids_and_dense_diagnostic_limit():
    model = EdgeReduction(make_walk("path", 3, "identity"))
    for bad in (np.eye(4), [1, 1, 0, 0], np.full(4, np.nan)):
        with pytest.raises(ValueError): model.prepare_q2(bad)
    with pytest.raises(ValueError): model.apply_M([.5, .5])
    with pytest.raises(ValueError): model.apply_M([2, -1, 0, 0])
    for bad in (-1, 4, True, 1.5):
        with pytest.raises(ValueError): model.atom_ket(bad)
    with pytest.raises(ValueError): model.transition_matrix(max_dimension=3)
    with pytest.raises(ValueError): list(model.iter_mean(np.ones(4) / 2, -1))


def test_reduced_evolution_never_requests_dense_M_U_or_channel(monkeypatch):
    walk = make_walk("star", 8, "random")
    def forbidden(*args, **kwargs): raise AssertionError("Dense/reference allocation on reduced path")
    monkeypatch.setattr(ScatteringWalk, "operator", property(forbidden))
    monkeypatch.setattr(ScatteringWalk, "apply_channel", forbidden)
    monkeypatch.setattr(EdgeReduction, "transition_matrix", forbidden)
    model = EdgeReduction(walk)
    initial = np.ones(walk.graph.dimension) / np.sqrt(walk.graph.dimension)
    for frame in model.iter_mean(initial, 10):
        assert frame.born_edges().sum() == pytest.approx(1)
    result = OptimizedEdgeTrajectory(model, seed=3).run(initial, 20)
    assert result.states[-1].atom_id is not None
