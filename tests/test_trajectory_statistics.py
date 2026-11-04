"""E-09 on actual SQW atoms: phases, timing, compact paths and X-01/X-04."""
import numpy as np
import pytest
from numpy.testing import assert_allclose
from sqw.core import TrajectoryStatistics, ScatteringWalk, GraphModel, OptimizedVertexTrajectory
from test_edge_markov import make_walk, initial_state
from test_vertex_markov import vertex_fixture
from test_stationary import x04_walk


@pytest.mark.parametrize('r', [0., .01, .2, .5, .9])
def test_X01_actual_scattering_basis_and_variance(r):
    graph = GraphModel.preset('path',3)
    walk = ScatteringWalk(graph,{0:np.eye(1),1:np.array([[np.sqrt(r),np.sqrt(1-r)],
        [np.sqrt(1-r),-np.sqrt(r)]]),2:np.eye(1)})
    engine = TrajectoryStatistics(walk)
    # Handoff basis (xy),(zy),(yx),(yz), x=0,y=1,z=2.
    order = [graph.edge_index[e] for e in [(0,1),(2,1),(1,0),(1,2)]]
    m = engine.model.sparse_M.toarray()[np.ix_(order,order)]
    assert_allclose(m,[[0,0,r,1-r],[0,0,1-r,r],[1,0,0,0],[0,1,0,0]],atol=1e-15)
    f = engine.observable(index=graph.edge_index[(0,1)])
    result = engine.analyze(np.eye(4)/4,f).classes[0].poisson
    assert_allclose(result.mean,.25)
    assert_allclose(result.asymptotic_variance,r/(8*(1-r)),atol=2e-14)
    assert result.period == (4 if r==0 else 2)


@pytest.mark.parametrize('vertex', [False,True])
def test_quantum_observables_against_direct_density_and_measurement_timing(vertex):
    walk = vertex_fixture('cycle',3,'random') if vertex else make_walk('cycle',3,'random')
    engine = TrajectoryStatistics(walk)
    model,d = engine.model,engine.model.dimension
    rng = np.random.default_rng(98)
    a = rng.normal(size=(d,d))+1j*rng.normal(size=(d,d)); a += a.conj().T
    f = engine.observable('quantum',matrix=a)
    labels = model.graph.vertices if vertex else range(d)
    assert_allclose(f,[np.trace(a@model.atom_density(x)).real for x in labels],atol=3e-14)
    for v in model.graph.vertices:
        probability = engine.observable('vertex_probability',vertex=v)
        ids = [model.graph.vertex_index[v]] if vertex else model.graph.incoming_indices(v)
        assert_allclose(probability,[np.diag(model.atom_density(x)).real[ids].sum() for x in labels],atol=3e-14)
        outcomes = engine.observable('outcome_indicator',vertex=v)
        expected = [float(x==v) for x in labels] if vertex else [float(x==v) for x,y in model.graph.directed_edges]
        assert_allclose(outcomes,expected)
        assert np.linalg.norm(outcomes-probability) > .01
    if vertex:
        shifted = engine.with_beta({0:1.3,1:-.4,2:2.1})
        assert shifted.statistics is engine.statistics
        assert shifted.model._p is model._p
        assert np.linalg.norm(shifted.observable('quantum',matrix=a)-f) > .01
        assert_allclose(shifted.observable(),engine.observable())
    f[:] = 100
    assert np.max(abs(engine.observable('quantum',matrix=a))) < 100  # defensive cached copy


def test_vertex_same_seed_matches_existing_compact_engine_and_direct_means():
    walk = vertex_fixture('cycle',3,'random')
    engine = TrajectoryStatistics(walk)
    initial = initial_state(3,True)
    f = engine.observable('coherence_imag',index=0,second=1)
    result = engine.sample(initial,f,71,seed=91,burn_in=7)
    path = OptimizedVertexTrajectory(engine.model,seed=91).run(initial,78)
    ids = [walk.graph.vertex_index[s.outcome] for s in path.states[8:]]
    assert [p.atom_id for p in result.points] == ids
    assert_allclose([p.mean for p in result.points],np.cumsum(f[ids])/np.arange(1,72),atol=1e-15)
    assert (result.atom_start_step,result.first_step,result.last_step)==(1,8,78)
    assert_allclose(np.array(result.empirical_law)@f,result.empirical_mean,atol=1e-15)


def test_zero_variance_is_not_zero_finite_error_and_no_density_history(monkeypatch):
    engine = TrajectoryStatistics(make_walk('path',3,'grover'))
    monkeypatch.setattr(engine.model,'atom_density',lambda *_: pytest.fail('dense history'))
    f = engine.observable()
    result = engine.sample(np.eye(4)[0],f,5,seed=0)
    assert result.confidence_interval is None
    assert all(p.half_width is None for p in result.points)
    assert abs(result.empirical_mean-.25) > 0
    assert result == engine.sample(np.eye(4)[0],f,5,seed=0)
    downsampled = engine.sample(np.eye(4)[0],f,501,seed=0,max_points=17)
    assert len(downsampled.points)==17
    assert (downsampled.points[0].samples,downsampled.points[-1].samples)==(1,501)


def test_X04_transient_and_artificial_stationary_start():
    engine = TrajectoryStatistics(x04_walk())
    initial = np.eye(5)[2]
    f = engine.observable(index=0)
    result = engine.analyze(initial,f)
    assert result.initial_transient_mass == 1
    assert_allclose([c.absorption_probability for c in result.classes],[1,0],atol=1e-14)
    assert_allclose(result.classes[0].poisson.mean,2/3)
    assert_allclose(result.classes[0].poisson.asymptotic_variance,2/27)
    path = engine.sample(initial,f,300,seed=5)
    assert path.points[0].atom_id==2 and path.entered_class==0
    assert path.class_entry_step > 1
    assert path.support_sensitive and path.confidence_interval is None
    other = engine.sample(initial,f,100,seed=8,start='stationary_class',class_index=1)
    assert other.stationary_start_requested and other.requested_class==1
    assert all(p.atom_id in (3,4) for p in other.points)


@pytest.mark.parametrize('kwargs', [{'samples':0},{'samples':True},{'samples':2,'burn_in':-1},
    {'samples':2,'confidence':1.},{'samples':2,'max_points':1},{'samples':2,'start':'unknown'}])
def test_invalid_sampling_contract(kwargs):
    engine = TrajectoryStatistics(make_walk('path',3,'hadamard'))
    with pytest.raises(ValueError): engine.sample(np.eye(4)[0],engine.observable(),**kwargs)


@pytest.mark.parametrize('kwargs', [{'index':9},{'kind':'quantum','matrix':[[0,1],[0,0]]},
    {'kind':'label_values','values':[1,2j,3,4]},{'kind':'coherence_real','second':0},
    {'kind':'vertex_probability','vertex':99}])
def test_invalid_observables(kwargs):
    with pytest.raises(ValueError): TrajectoryStatistics(make_walk('path',3,'hadamard')).observable(**kwargs)
