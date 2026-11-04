"""Tests for the independent Section-6 model, including complex boundary data."""

import numpy as np
import pytest
from numpy.testing import assert_allclose

from sqw.core import GraphModel, ScatteringWalk, density_from_state, scattering_matrix
from sqw.core.vertex import InducedVertexWalk


def edge_walk(kind="cycle", preset="random"):
    graph = GraphModel.preset(kind, 3)
    rng = np.random.default_rng(812)
    return ScatteringWalk(graph, {
        x: scattering_matrix(preset, graph.degree(x), rng) for x in graph.vertices
    })


def test_complex_boundary_compression_matches_theta_with_conjugation():
    edge = edge_walk()
    omega = {
        0: np.array([1, 2j]) / np.sqrt(5),
        1: np.array([1j, 1]) / np.sqrt(2),
        2: np.array([1 + 1j, -2j]) / np.sqrt(6),
    }
    vertex = InducedVertexWalk(edge, omega, {0: 0.2, 1: -0.5, 2: 1.7})
    r = vertex.boundary_operator
    assert_allclose(r @ r.conj().T, np.eye(3), atol=1e-12)
    for i, k in enumerate(edge.kraus_operators()):
        compressed = r @ k @ r.conj().T
        expected = np.zeros((3, 3), dtype=complex)
        expected[:, i] = vertex.theta[edge.graph.vertices[i]]
        assert_allclose(compressed, expected, atol=1e-12)
    assert any(abs(v.imag).max() > 0.1 for v in vertex.theta.values())


@pytest.mark.parametrize("kind", ["path", "cycle"])
def test_vertex_kraus_completeness_and_quantum_markov_correspondence(kind):
    vertex = InducedVertexWalk(edge_walk(kind), beta={0: 0.3, 1: -0.9, 2: 2.1})
    ks = vertex.kraus_operators()
    assert_allclose(sum(k.conj().T @ k for k in ks), np.eye(3), atol=1e-12)
    transition = vertex.markov_matrix
    assert np.all(transition >= 0)
    assert_allclose(transition.sum(axis=1), np.ones(3), atol=1e-12)
    psi = np.array([1, 1j, -1]) / np.sqrt(3)
    rho = density_from_state(psi)
    classical = np.diag(rho).real.copy()
    for _ in range(9):
        expected = sum(k @ rho @ k.conj().T for k in ks)
        rho = vertex.step_density(rho)
        classical = classical @ transition
        assert_allclose(rho, expected, atol=1e-12)
        assert_allclose(rho, rho.conj().T, atol=1e-12)
        assert_allclose(np.trace(rho), 1, atol=1e-12)
        assert np.linalg.eigvalsh(rho).min() > -1e-12
        assert_allclose(vertex.vertex_probabilities(rho), classical, atol=1e-12)


def test_path_grover_vertex_has_self_loop_and_is_not_edge_marginal():
    edge = edge_walk("path", "grover")
    vertex = InducedVertexWalk(edge)
    assert_allclose(vertex.markov_matrix,
                    [[0.5, 0.5, 0], [0.5, 0, 0.5], [0, 0.5, 0.5]], atol=1e-12)
    rho = np.diag([1, 0, 0]).astype(complex)
    vertex_distribution = vertex.vertex_probabilities(vertex.step_density(rho))
    r = vertex.boundary_operator
    edge_distribution = edge.vertex_probabilities(edge.step_density(r.conj().T @ rho @ r))
    assert_allclose(vertex_distribution, [0.5, 0.5, 0], atol=1e-12)
    assert_allclose(edge_distribution, [0, 1, 0], atol=1e-12)
    # Omitting the chi completion would lose probability mass in this case.
    compressed = r @ edge.step_density(r.conj().T @ rho @ r) @ r.conj().T
    assert np.trace(compressed).real == pytest.approx(0.5)


def test_beta_changes_coherences_but_not_transition_probabilities():
    edge = edge_walk("path", "grover")
    a = InducedVertexWalk(edge)
    b = InducedVertexWalk(edge, beta={0: np.pi / 2, 1: 0, 2: 0})
    rho = np.diag([1, 0, 0])
    assert_allclose(a.markov_matrix, b.markov_matrix, atol=1e-12)
    assert not np.allclose(a.step_density(rho), b.step_density(rho))
    assert_allclose(a.step_density(rho)[0, 1], 0.5, atol=1e-12)
    assert_allclose(b.step_density(rho)[0, 1], 0.5j, atol=1e-12)


def test_vertex_inputs_rejected_and_evolution_zero_step():
    edge = edge_walk()
    with pytest.raises(ValueError):
        InducedVertexWalk(edge, omega={0: [1, 0]})
    with pytest.raises(ValueError):
        InducedVertexWalk(edge, omega={x: [1, 1] for x in range(3)})
    with pytest.raises(ValueError):
        InducedVertexWalk(edge, beta={0: 0, 1: 0, 2: np.nan})
    with pytest.raises(ValueError):
        InducedVertexWalk(edge, beta={0: 0, 1: 0, 2: 1j})
    vertex = InducedVertexWalk(edge)
    with pytest.raises(ValueError):
        vertex.step_density(np.eye(3))
    initial = np.eye(3) / 3
    assert len(vertex.evolve_density(initial, 0)) == 1
    assert_allclose(vertex.evolve_density(initial, 0)[0], initial)
