"""Independent mathematical regressions for Joye's edge conventions and channels."""

import numpy as np
import pytest
from numpy.testing import assert_allclose

from sqw.core import (
    GraphModel,
    ReferenceTrajectory,
    ScatteringWalk,
    basis_state,
    density_from_state,
    scattering_matrix,
    uniform_state,
    validate_density,
    validate_pure,
    validate_scattering,
)


def dense(matrix):
    return matrix.toarray() if hasattr(matrix, "toarray") else np.asarray(matrix)


def kraus(walk):
    result = walk.kraus_operators()
    return [dense(k) for k in (result.values() if isinstance(result, dict) else result)]


def make_walk(kind="path", size=3, preset="random", seed=19):
    graph = GraphModel.preset(kind, size)
    rng = np.random.default_rng(seed)
    return ScatteringWalk(
        graph,
        {x: scattering_matrix(preset, len(graph.neighbors[x]), rng=rng) for x in graph.vertices},
    )


def random_density(dimension, seed=71):
    rng = np.random.default_rng(seed)
    a = rng.normal(size=(dimension, dimension)) + 1j * rng.normal(size=(dimension, dimension))
    rho = a @ a.conj().T
    return rho / np.trace(rho)


def test_path_basis_and_insertion_independence():
    first = GraphModel.from_edges([2, 0, 1], [(2, 1), (1, 0)])
    second = GraphModel.preset("path", 3)
    expected = ((0, 1), (1, 0), (1, 2), (2, 1))
    assert first.vertices == (0, 1, 2)
    assert first.directed_edges == second.directed_edges == expected
    assert first.neighbors[1] == (0, 2)
    assert first.dimension == 4
    assert dict(first.edge_index) == {edge: i for i, edge in enumerate(expected)}


def test_integer_labels_are_not_array_positions():
    graph = GraphModel.from_edges([11, -4, 30], [(30, 11), (-4, 11)])
    assert graph.vertices == (-4, 11, 30)
    assert graph.directed_edges == ((-4, 11), (11, -4), (11, 30), (30, 11))
    state = basis_state(graph, (11, -4))
    walk = ScatteringWalk(graph, {x: np.eye(len(graph.neighbors[x])) for x in graph.vertices})
    assert_allclose(walk.vertex_probabilities(state), [0, 1, 0])
    assert_allclose(walk.step_pure(state), basis_state(graph, (-4, 11)))


@pytest.mark.parametrize("edge", [(True, 0), (1.0, 0), ("1", 0)])
def test_basis_state_does_not_alias_non_integer_vertex_labels(edge):
    with pytest.raises(ValueError, match="integer"):
        basis_state(GraphModel.preset("path", 3), edge)


@pytest.mark.parametrize("nodes,edges", [
    ([], []), ([0], []), ([0, 1], []), ([0, 1], [(0, 0)]),
    ([0, 1], [(0, 2)]), ([0, 1], [(0, 1), (1, 0)]),
    ([0, 0, 1], [(0, 1)]),
])
def test_invalid_graphs_rejected(nodes, edges):
    with pytest.raises(ValueError):
        GraphModel.from_edges(nodes, edges)


@pytest.mark.parametrize("kind,size,dimension", [
    ("path", 3, 4), ("cycle", 3, 6), ("complete", 4, 12), ("star", 5, 8),
])
def test_graph_presets(kind, size, dimension):
    graph = GraphModel.preset(kind, size)
    assert len(graph.vertices) == size
    assert graph.dimension == dimension
    assert all((y, x) in graph.edge_index for x, y in graph.directed_edges)


@pytest.mark.parametrize("preset", ["identity", "grover", "dft", "random"])
@pytest.mark.parametrize("degree", [1, 2, 3, 7])
def test_scattering_presets_are_unitary(preset, degree):
    matrix = scattering_matrix(preset, degree, rng=np.random.default_rng(11))
    assert matrix.shape == (degree, degree)
    assert_allclose(matrix.conj().T @ matrix, np.eye(degree), atol=1e-12, rtol=0)
    assert_allclose(matrix @ matrix.conj().T, np.eye(degree), atol=1e-12, rtol=0)


def test_hadamard_and_grover_values():
    assert_allclose(scattering_matrix("hadamard", 2), np.array([[1, 1], [1, -1]]) / np.sqrt(2))
    assert_allclose(scattering_matrix("grover", 3), 2 * np.ones((3, 3)) / 3 - np.eye(3))
    with pytest.raises(ValueError):
        scattering_matrix("hadamard", 3)


def test_seeded_random_scattering():
    assert_allclose(
        scattering_matrix("random", 4, rng=np.random.default_rng(9)),
        scattering_matrix("random", 4, rng=np.random.default_rng(9)), atol=0, rtol=0,
    )


@pytest.mark.parametrize("matrix", [
    np.ones((2, 2)), np.eye(3), [[1, 0], [0, 1.00001]],
    [[1, 0], [0, np.nan]], [[1, 0], [0, np.inf]],
])
def test_invalid_scattering_rejected(matrix):
    with pytest.raises(ValueError):
        validate_scattering(matrix, 2)


def test_path_hadamard_operator_exact_orientation():
    graph = GraphModel.preset("path", 3)
    walk = ScatteringWalk(graph, {0: np.eye(1), 1: scattering_matrix("hadamard", 2), 2: np.eye(1)})
    h = 1 / np.sqrt(2)
    expected = np.array([[0, h, h, 0], [1, 0, 0, 0], [0, 0, 0, 1], [0, h, -h, 0]])
    assert_allclose(dense(walk.operator), expected, atol=1e-12, rtol=0)
    assert_allclose(walk.step_pure(basis_state(graph, (1, 2))), [h, 0, 0, -h], atol=1e-12)


def test_nonsymmetric_complex_scattering_keeps_row_column_convention():
    graph = GraphModel.preset("path", 3)
    walk = ScatteringWalk(graph, {0: [[1]], 1: [[0, 1j], [1, 0]], 2: [[1]]})
    # Incoming from 0 is column 0; outgoing toward 2 is row 1.
    assert_allclose(walk.step_pure(basis_state(graph, (1, 0))), [0, 0, 0, 1], atol=1e-12)
    # Incoming from 2 is column 1; outgoing toward 0 carries phase i.
    assert_allclose(walk.step_pure(basis_state(graph, (1, 2))), [1j, 0, 0, 0], atol=1e-12)


def test_fourier_positive_exponent_convention():
    omega = np.exp(2j * np.pi / 3)
    expected = np.array([[1, 1, 1], [1, omega, omega**2], [1, omega**2, omega]]) / np.sqrt(3)
    assert_allclose(scattering_matrix("dft", 3), expected, atol=1e-12, rtol=0)


@pytest.mark.parametrize("kind", ["path", "cycle"])
def test_global_unitarity_projectors_and_kraus_completeness(kind):
    walk = make_walk(kind)
    d = walk.graph.dimension
    u = dense(walk.operator)
    identity = np.eye(d)
    assert_allclose(u.conj().T @ u, identity, atol=1e-12, rtol=0)
    assert_allclose(u @ u.conj().T, identity, atol=1e-12, rtol=0)
    projectors = [dense(walk.incoming_projector(x)) for x in walk.graph.vertices]
    assert_allclose(sum(projectors), identity, atol=1e-12, rtol=0)
    for i, p in enumerate(projectors):
        assert_allclose(p @ p, p)
        for j, q in enumerate(projectors):
            if i != j:
                assert_allclose(p @ q, np.zeros((d, d)))
    ks = kraus(walk)
    assert_allclose(sum(k.conj().T @ k for k in ks), identity, atol=1e-12, rtol=0)
    assert_allclose(sum(k @ k.conj().T for k in ks), identity, atol=1e-12, rtol=0)


@pytest.mark.parametrize("kind", ["path", "cycle"])
def test_open_channel_matches_full_kraus_sum_and_remains_a_density(kind):
    walk = make_walk(kind)
    rho = random_density(walk.graph.dimension)
    ks = kraus(walk)
    for _ in range(12):
        expected = sum(k @ rho @ k.conj().T for k in ks)
        rho = walk.step_density(rho)
        assert_allclose(rho, expected, atol=1e-12, rtol=0)
        assert_allclose(rho, rho.conj().T, atol=1e-12, rtol=0)
        assert_allclose(np.trace(rho), 1, atol=1e-12, rtol=0)
        assert np.linalg.eigvalsh(rho).min() >= -1e-12
        assert_allclose(sum(walk.edge_probabilities(rho)), 1, atol=1e-12)
        assert_allclose(sum(walk.vertex_probabilities(rho)), 1, atol=1e-12)


def test_open_measurement_preserves_within_vertex_coherence():
    walk = make_walk("path", preset="identity")
    psi = np.array([0, 1, 1j, 0]) / np.sqrt(2)
    expected = density_from_state(walk.step_pure(psi))
    rho = walk.step_density(density_from_state(psi))
    assert_allclose(rho, expected, atol=1e-12)
    assert abs(rho[0, 3]) == pytest.approx(0.5)
    # Coherence between different incoming vertices is measured away.
    psi = np.array([1, 1, 0, 0]) / np.sqrt(2)
    rho = walk.step_density(density_from_state(psi))
    assert_allclose(rho, np.diag([0.5, 0.5, 0, 0]), atol=1e-12)


@pytest.mark.parametrize("kind", ["path", "cycle"])
def test_pure_evolution_and_marginals(kind):
    walk = make_walk(kind)
    psi = uniform_state(walk.graph)
    for _ in range(20):
        psi = walk.step_pure(psi)
        assert_allclose(np.vdot(psi, psi), 1, atol=1e-12)
        edges = walk.edge_probabilities(psi)
        expected = [sum(edges[i] for i, (target, _) in enumerate(walk.graph.directed_edges) if target == x)
                    for x in walk.graph.vertices]
        assert_allclose(walk.vertex_probabilities(psi), expected, atol=1e-12)


def test_invalid_states_rejected_without_normalizing():
    for state in [np.zeros(4), np.ones(4), [np.nan, 0, 0, 0]]:
        with pytest.raises(ValueError):
            validate_pure(state, 4)
    nonhermitian = np.diag([0.5, 0.5, 0, 0]).astype(complex)
    nonhermitian[0, 1] = 0.1j
    for rho in [np.eye(4), np.diag([1.1, -0.1, 0, 0]), nonhermitian,
                np.eye(2) / 2, np.full((4, 4), np.nan)]:
        with pytest.raises(ValueError):
            validate_density(rho, 4)


@pytest.mark.parametrize("mixed", [False, True])
def test_trajectory_seed_timing_reduction_and_born_probabilities(mixed):
    walk = make_walk("cycle")
    initial = random_density(6) if mixed else uniform_state(walk.graph)
    a = ReferenceTrajectory(walk, seed=601).run(initial, 8)
    b = ReferenceTrajectory(walk, seed=601).run(initial, 8)
    assert list(a.outcomes) == list(b.outcomes)
    assert len(a.states) == 9
    assert len(a.reduced_states) == len(a.probabilities) == len(a.selected_probabilities) == 8
    u = dense(walk.operator)
    for j, x in enumerate(a.outcomes):
        state = a.states[j]
        p = dense(walk.incoming_projector(x))
        probabilities = walk.vertex_probabilities(state)
        selected = probabilities[walk.graph.vertices.index(x)]
        assert_allclose(a.probabilities[j], probabilities, atol=1e-12)
        assert_allclose(sum(a.probabilities[j]), 1, atol=1e-12)
        assert a.selected_probabilities[j] == pytest.approx(selected)
        assert selected > 0
        reduction = p @ state @ p / selected if mixed else p @ state / np.sqrt(selected)
        expected = u @ reduction @ u.conj().T if mixed else u @ reduction
        assert_allclose(a.reduced_states[j], reduction, atol=1e-12)
        assert_allclose(a.states[j + 1], expected, atol=1e-12)
        assert_allclose(a.states[j + 1], b.states[j + 1], atol=0, rtol=0)


def test_zero_steps_and_deterministic_zero_probability_branches():
    walk = make_walk("path", preset="identity")
    initial = basis_state(walk.graph, (1, 0))
    zero = ReferenceTrajectory(walk, seed=7).run(initial, 0)
    assert len(zero.states) == 1
    assert len(zero.outcomes) == 0
    assert_allclose(zero.states[0], initial)
    result = ReferenceTrajectory(walk, seed=7).run(initial, 4)
    assert list(result.outcomes) == [1, 0, 1, 0]
    assert_allclose(result.selected_probabilities, np.ones(4))


def exact_branches(walk, initial, steps):
    """Enumerate measurement histories independently with dense projectors."""
    u = dense(walk.operator)
    branches = [(1.0, initial)]
    for _ in range(steps):
        following = []
        for weight, rho in branches:
            for x in walk.graph.vertices:
                p = dense(walk.incoming_projector(x))
                block = p @ rho @ p
                probability = float(np.trace(block).real)
                if probability > 1e-14:
                    following.append((weight * probability, u @ block @ u.conj().T / probability))
        branches = following
    return branches


@pytest.mark.parametrize("kind", ["path", "cycle"])
def test_exact_trajectory_branch_average_matches_channel(kind):
    walk = make_walk(kind)
    rho = random_density(walk.graph.dimension)
    branches = exact_branches(walk, rho, 4)
    expected = rho
    for _ in range(4):
        expected = walk.step_density(expected)
    assert_allclose(sum(weight for weight, _ in branches), 1, atol=1e-12)
    assert_allclose(sum(weight * state for weight, state in branches), expected, atol=1e-12)


@pytest.mark.parametrize("kind", ["path", "cycle"])
def test_monte_carlo_full_density_agrees_with_exact_channel(kind):
    walk = make_walk(kind)
    d = walk.graph.dimension
    psi = np.arange(1, d + 1) + 1j * np.arange(d, 0, -1)
    psi = psi / np.linalg.norm(psi)
    rho = density_from_state(psi)
    branches = exact_branches(walk, rho, 3)
    expected = rho
    for _ in range(3):
        expected = walk.step_density(expected)
    count = 2500
    sampler = ReferenceTrajectory(walk, seed=411)
    average = np.zeros_like(rho)
    for _ in range(count):
        final = sampler.run(psi, 3).states[-1]
        average += density_from_state(final) / count
    # Bernstein inequality for each real/imaginary component, union bound
    # over 2*d*d components. |X-E[X]| <= 2 for density entries; alpha=1e-6.
    log_factor = np.log(4 * d * d / 1e-6)
    for component in (np.real, np.imag):
        variance = sum(weight * (component(state) - component(expected)) ** 2
                       for weight, state in branches)
        tolerance = np.sqrt(2 * variance * log_factor / count) + 4 * log_factor / (3 * count)
        assert np.all(np.abs(component(average - expected)) <= tolerance)


def test_mixed_trajectory_becomes_pure_after_second_step():
    walk = make_walk("cycle")
    result = ReferenceTrajectory(walk, seed=12).run(np.eye(6) / 6, 4)
    assert np.trace(result.states[1] @ result.states[1]).real == pytest.approx(0.5)
    for rho in result.states[2:]:
        assert np.trace(rho @ rho).real == pytest.approx(1)
