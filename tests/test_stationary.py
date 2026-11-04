"""E-06/E-07, V-04/V-05, NEW-04 and exact X-04/AUD-01 counterexample."""
import numpy as np
import pytest
from numpy.testing import assert_allclose

from sqw.core import (StationaryAnalysis, EdgeReduction, VertexReduction,
    InducedVertexWalk, ScatteringWalk, GraphModel, scattering_matrix)
from test_edge_markov import make_walk, initial_state


@pytest.mark.parametrize('preset,classes,period', [('identity', 2, 2), ('hadamard', 1, 2), ('grover', 1, 4)])
def test_path3_edge_identity_hadamard_and_swap(preset, classes, period):
    # At degree two Grover is precisely Swap; endpoints are identity.
    walk = make_walk('path', 3, preset)
    analysis = StationaryAnalysis(walk)
    chain = analysis.chain
    assert analysis.orientation == 'column' and analysis.start_step == 2
    assert analysis.support_source == 'analytic_builtin'
    assert len(chain.closed_classes) == classes
    assert chain.transient_states == () and chain.bistochastic
    assert [c.period for c in chain.closed_classes] == [period] * classes
    for c in chain.closed_classes:
        assert_allclose(c.stationary, np.ones(len(c.states)) / len(c.states), atol=1e-14)
    initial = np.eye(4)[0]
    mixture = analysis.mixture(initial)
    assert not mixture.ordinary_guaranteed
    assert_allclose(mixture.class_weights.sum(), 1)
    # Explicit orientation adapter, never silently use M as row matrix.
    assert_allclose(chain.raw_transition.toarray(), analysis.model.transition_matrix().T)
    frames = list(analysis.evolve(initial, period * 40 - 1))
    assert frames[0].step == 2
    q2 = analysis.initial_law(initial)
    explicit = np.array([q2 @ np.linalg.matrix_power(chain.raw_transition.toarray(), k) for k in range(len(frames))])
    assert_allclose(frames[-1].cesaro, explicit.mean(axis=0), atol=2e-14)
    # Hadamard has an initial nonperipheral component: even a whole number
    # of periods need not give the limit exactly in a finite Cesaro window.
    assert frames[-1].cesaro_total_variation <= 1 / len(frames) + 2e-14
    assert frames[-1].total_variation > .1


def test_reducible_edge_input_mixture_and_canonical_state():
    walk = make_walk('path', 3, 'identity')
    analysis = StationaryAnalysis(walk)
    initial = np.diag([.1, .2, .3, .4])
    q2 = analysis.model.prepare_q2(initial)
    mixture = analysis.mixture(initial)
    assert_allclose(mixture.class_weights, [q2[list(c.states)].sum() for c in analysis.chain.closed_classes])
    assert_allclose(mixture.stationary, [.15, .15, .35, .35])
    for i in range(2):
        rho = analysis.stationary_density(class_index=i)
        assert_allclose(walk.apply_channel(rho), rho, atol=2e-14)
    assert_allclose(analysis.model.mean_density(np.ones(4)/4), np.eye(4)/4, atol=2e-14)
    assert not analysis.chain.unique_stationary


@pytest.mark.parametrize('preset', ['dft', 'random'])
def test_triangle_edge_aperiodicity_and_trace_distance_identity(preset):
    walk = make_walk('cycle', 3, preset)
    analysis = StationaryAnalysis(walk)
    assert analysis.chain.irreducible and analysis.chain.ordinary_for_all_initials
    initial = initial_state(6, True)
    limit = analysis.stationary_density(initial)
    assert_allclose(limit, np.eye(6)/6, atol=2e-14)
    frames = list(analysis.evolve(initial, 40))
    rho = walk.apply_channel(walk.apply_channel(initial))
    for f in frames:
        assert_allclose(analysis.model.mean_density(f.probabilities), rho, atol=3e-13)
        assert_allclose(abs(np.linalg.eigvalsh(rho-limit)).sum()/2, f.total_variation, atol=3e-13)
        rho = walk.apply_channel(rho)
    assert frames[-1].total_variation < frames[0].total_variation


@pytest.mark.parametrize('alpha', [0., .7, np.pi])
@pytest.mark.parametrize('kind,size', [('path', 3), ('star', 5), ('cycle', 3), ('path', 2)])
def test_generalized_grover_uniform_stationary_and_period_exception(alpha, kind, size):
    graph = GraphModel.preset(kind, size)
    coins = {}
    for x in graph.vertices:
        w = np.ones(graph.degree(x))/np.sqrt(graph.degree(x)); q = np.outer(w, w)
        coins[x] = q + np.exp(1j*alpha)*(np.eye(len(w))-q)
    walk = InducedVertexWalk(ScatteringWalk(graph, coins))
    analysis = StationaryAnalysis(walk)
    assert analysis.chain.irreducible and analysis.chain.unique_stationary
    assert analysis.chain.closed_classes[0].period == (2 if size == 2 else 1)
    assert_allclose(analysis.chain.stationary_basis.toarray(), [np.ones(size)/size], atol=2e-14)
    rho = analysis.stationary_density(class_index=0)
    assert_allclose(walk.apply_channel(rho), rho, atol=2e-14)
    assert_allclose(np.diag(rho).real, np.ones(size)/size, atol=2e-14)
    if size > 2: assert np.linalg.norm(rho-np.eye(size)/size) > .1


def x04_walk():
    # GraphModel stores ascending ports. Convert the handoff's port order
    # 3:[4,2] explicitly into stored 3:[2,4], on BOTH rows and columns.
    graph = GraphModel.preset('path', 5)
    coins = {x: scattering_matrix('dft', graph.degree(x)) for x in graph.vertices}
    swap = np.array([[0, 1], [1, 0]])
    coins[3] = swap @ coins[3] @ swap.T
    return InducedVertexWalk(ScatteringWalk(graph, coins))


def test_X04_AUD01_two_closed_cycles_and_transient_vertex2():
    walk = x04_walk()
    p = np.array([[.5,.5,0,0,0], [1,0,0,0,0], [0,.5,.5,0,0], [0,0,0,0,1], [0,0,0,.5,.5]])
    assert_allclose(walk.markov_matrix, p, atol=2e-15)
    analysis = StationaryAnalysis(walk)
    assert analysis.chain.transient_states == (2,)
    assert [c.states for c in analysis.chain.closed_classes] == [(0,1), (3,4)]
    assert [c.period for c in analysis.chain.closed_classes] == [1,1]
    rho0 = np.diag([0,0,1,0,0])
    mixture = analysis.mixture(rho0)
    assert_allclose(mixture.class_weights, [1,0], atol=2e-14)
    assert_allclose(mixture.stationary, [2/3,1/3,0,0,0], atol=2e-14)
    assert_allclose(analysis.chain.absorption.toarray(), [[1,0],[1,0],[1,0],[0,1],[0,1]], atol=2e-14)
    assert mixture.ordinary_guaranteed and not analysis.chain.unique_stationary
    rho = rho0.copy()
    for _ in range(200): rho = walk.apply_channel(rho)
    assert_allclose(rho, analysis.stationary_density(rho0), atol=3e-13)
    assert_allclose(np.diag(rho).real, mixture.stationary, atol=3e-13)
    assert_allclose(np.eye(5)[2] @ np.linalg.matrix_power(p, 200), mixture.stationary, atol=2e-14)


@pytest.mark.parametrize('kind,size', [('path',5), ('star',5), ('cycle',5), ('complete',5)])
def test_DFT_analytical_support_excludes_roundoff_but_preserves_raw_states(kind, size):
    walk = InducedVertexWalk(make_walk(kind,size,'dft'))
    analysis = StationaryAnalysis(walk)
    assert analysis.support_source == 'analytic_builtin'
    for i,x in enumerate(walk.graph.vertices):
        neighbor = walk.graph.neighbors[x][0]
        expected = {walk.graph.vertex_index[neighbor]}
        if walk.graph.degree(neighbor)>1: expected.add(i)
        assert set(analysis.chain.transition.getrow(i).indices) == expected
    assert all(c.period == 1 for c in analysis.chain.closed_classes)
    assert_allclose(analysis.chain.raw_transition.toarray(), walk.markov_matrix, atol=0, rtol=0)


def test_complex_stationary_quantum_reconstruction_and_beta_cache_reuse():
    edge = make_walk('cycle',3,'random')
    omega = {x: np.array([.6,.8j]) for x in edge.graph.vertices}
    vertex = InducedVertexWalk(edge,omega,{0:.3,1:-.7,2:1.1})
    analysis = StationaryAnalysis(vertex)
    q0 = initial_state(3, True)
    rho = analysis.stationary_density(q0)
    assert_allclose(vertex.apply_channel(rho),rho,atol=2e-14)
    assert_allclose(np.trace(rho),1,atol=2e-14)
    assert np.linalg.eigvalsh(rho).min() >= -1e-14
    shifted = analysis.with_beta({0:1.2,1:.4,2:-.2})
    assert shifted.chain is analysis.chain
    assert shifted.model._p is analysis.model._p
    assert_allclose(shifted.mixture(q0).stationary,analysis.mixture(q0).stationary,atol=0,rtol=0)
    assert np.linalg.norm(shifted.stationary_density(q0)-rho) > .05
    independent = InducedVertexWalk(edge,omega,{0:1.2,1:.4,2:-.2})
    assert_allclose(independent.apply_channel(shifted.stationary_density(q0)),shifted.stationary_density(q0),atol=2e-14)
    reconstruction = sum(weight*shifted.model.atom_density(label) for label,weight in shifted.invariant_measure(q0))
    assert_allclose(reconstruction, shifted.stationary_density(q0),atol=2e-14)


def test_sparse_adapters_and_initial_changes_reuse_structure(monkeypatch):
    monkeypatch.setattr(EdgeReduction,'transition_matrix',lambda *_args,**_kwargs: pytest.fail('dense M'))
    monkeypatch.setattr(VertexReduction,'transition_matrix',lambda *_args,**_kwargs: pytest.fail('dense P'))
    analysis = StationaryAnalysis(make_walk('path',3,'identity'))
    structure = analysis.chain
    a,b = analysis.mixture(np.eye(4)[0]),analysis.mixture(np.eye(4)[3])
    assert analysis.chain is structure and not np.array_equal(a.class_weights,b.class_weights)
    assert_allclose(analysis.chain.stationary_basis.sum(axis=1),1)
    StationaryAnalysis(InducedVertexWalk(make_walk('path',3,'dft')))
    with pytest.raises(ValueError): analysis.with_beta({})
    with pytest.raises(ValueError): analysis.stationary_density(class_index=5)
