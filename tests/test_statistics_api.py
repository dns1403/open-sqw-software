import pytest
from numpy.testing import assert_allclose
from fastapi.testclient import TestClient
from sqw.api.app import app, experiment
from sqw.api.schemas import StatisticsRequest
from sqw.api.statistics_cache import statistics_model
from test_markov_api import request

client = TestClient(app)


@pytest.mark.parametrize('mode,start,orientation', [('trajectory',2,'column'),('open',2,'column'),('vertex',1,'row')])
def test_statistics_schema_replay_timing_and_correlated_uncertainty(mode,start,orientation):
    payload = request(mode=mode,preset='dft',samples=1200,burn_in=3,trajectory_seed=80)
    response = client.post('/api/statistics',json=payload)
    assert response.status_code==200,response.text
    result = response.json()
    assert result==client.post('/api/statistics',json=payload).json()
    assert result['orientation']==orientation and result['start_step']==start
    path = result['trajectory']
    assert path['first_step']==start+3 and path['last_step']==start+1202
    assert len(path['points'])==1001
    assert path['points'][-1]['samples']==1200
    assert result['uncertainty'][0]['approximate'] and not result['uncertainty'][0]['simultaneous']
    assert_allclose(sum(path['empirical_law']),1)


def test_phase_cache_reuse_and_invalidation():
    def engine(**changes):
        edge,walk,_ = experiment(StatisticsRequest(**request(mode='vertex',**changes)))
        return statistics_model(edge,walk,support_atol=changes.get('support_atol',1e-14))
    a = engine()
    assert engine(samples=5,trajectory_seed=2,initial={'kind':'basis','vertex':1}) is a
    b = engine(vertex_parameters={'beta':{'0':1.,'1':-.5,'2':.3}})
    assert b is not a and b.statistics is a.statistics
    assert b.stationary.chain is a.stationary.chain
    assert abs(a.observable('coherence_real')[0]-b.observable('coherence_real')[0]) > .001
    assert engine(seed=12).statistics is not a.statistics
    assert engine(support_atol=1e-8).statistics is not a.statistics
    assert engine(vertex_parameters={'omega':{'0':[[1,0],[0,0]],'1':[[1,0],[0,0]],'2':[[1,0],[0,0]]}}).statistics is not a.statistics


@pytest.mark.parametrize('changes,code', [({'mode':'unitary'},'request_validation'),
    ({'samples':0},'request_validation'),({'confidence':1.},'request_validation'),
    ({'observable':{'kind':'coherence_real','index':0,'second':0}},'statistics_observable'),
    ({'stationary_class':100},'stationary_class'),
    ({'graph':{'kind':'complete','size':12},'samples':100000},'statistics_budget')])
def test_statistics_invalid_input(changes,code):
    response = client.post('/api/statistics',json=request(samples=10,**changes) if 'samples' not in changes else request(**changes))
    assert response.status_code==422,response.text
    assert response.json()['code']==code


def test_reducible_edge_has_no_global_gaussian():
    data = client.post('/api/statistics',json=request(graph={'kind':'path','size':3},preset='identity',
        initial={'kind':'maximally_mixed'},samples=13)).json()
    assert not data['analysis']['global_clt_available']
    assert data['analysis']['global_mean'] is None
    assert_allclose([c['poisson']['mean'] for c in data['analysis']['classes']],[.5,0])
    assert data['trajectory']['confidence_interval'] is None
