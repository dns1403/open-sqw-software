import numpy as np
import pytest
from fastapi.testclient import TestClient
from numpy.testing import assert_allclose
from sqw.api.app import app
from sqw.api.stationary_cache import _structural_model
from test_markov_api import request, encode

client = TestClient(app)


@pytest.mark.parametrize('mode,start,orientation', [('trajectory',2,'column'), ('open',2,'column'), ('vertex',1,'row')])
def test_stationary_route_orientation_history_and_quantum(mode,start,orientation):
    payload = request(mode=mode,preset='dft',analysis_steps=10,include_density=True)
    response = client.post('/api/stationary',json=payload)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data['orientation'] == orientation and data['start_step'] == start
    assert data['frames'][0]['step'] == start and data['frames'][-1]['step'] == start+10
    matrix = np.array(data['transition_matrix'])
    assert_allclose(matrix.sum(axis=1 if mode=='vertex' else 0),1,atol=2e-14)
    assert data['quantum']['channel_residual'] < 2e-14
    density = np.array(data['quantum']['density']); rho = density[...,0]+1j*density[...,1]
    assert_allclose(np.trace(rho),1,atol=2e-14)
    assert data['support']['source'] == 'analytic_builtin'
    assert_allclose(np.array(data['absorption']).sum(axis=1),1)


def test_X04_experiment_endpoint_and_absorption_mixture():
    # Same explicit port-basis conversion as the independent core fixture.
    from sqw.core import GraphModel, scattering_matrix
    graph = GraphModel.preset('path',5)
    coins = {str(x):scattering_matrix('dft',graph.degree(x)) for x in graph.vertices}
    swap = np.array([[0,1],[1,0]])
    coins['3'] = swap@coins['3']@swap.T
    payload = request(mode='vertex',graph={'kind':'path','size':5},
        scattering={x:encode(s) for x,s in coins.items()},initial={'kind':'basis','vertex':2},
        analysis_steps=100,include_density=True)
    data = client.post('/api/stationary',json=payload).json()
    assert data['transient_states'] == [2]
    assert_allclose(data['class_weights'],[1,0])
    assert_allclose(data['stationary_mixture'],[2/3,1/3,0,0,0],atol=2e-14)
    assert data['ordinary_guaranteed'] and not data['unique_stationary']
    assert data['frames'][-1]['total_variation'] < 1e-12
    other = client.post('/api/stationary',json={**payload,'stationary_class':1}).json()
    assert_allclose(other['quantum']['weights'],[0,0,0,1/3,2/3],atol=2e-14)
    assert other['quantum']['channel_residual'] < 2e-14


def test_cache_reuses_structure_for_initial_horizon_beta_but_invalidates_coins():
    _structural_model.cache_clear()
    payload = request(mode='vertex',preset='dft',analysis_steps=0,include_density=True)
    a = client.post('/api/stationary',json=payload).json()
    first = _structural_model.cache_info()
    b = client.post('/api/stationary',json={**payload, 'analysis_steps':8,
        'initial':{'kind':'basis','vertex':2}, 'vertex_parameters':{'beta':{'0':.3,'1':-.7,'2':1.1}}}).json()
    second = _structural_model.cache_info()
    assert first.misses == second.misses == 1 and second.hits == first.hits+1
    assert a['transition_matrix'] == b['transition_matrix']
    assert a['quantum']['density'] != b['quantum']['density']
    client.post('/api/stationary',json={**payload,'preset':'identity'})
    assert _structural_model.cache_info().misses == 2


@pytest.mark.parametrize('changes,code', [
    ({'stationary_class':100},'stationary_class'),
    ({'analysis_steps':5000,'graph':{'kind':'cycle','size':32}},'stationary_budget'),
    ({'include_density':True,'graph':{'kind':'complete','size':10}},'analysis_budget'),
    ({'analysis_steps':-1},'request_validation'),
    ({'support_atol':-1},'request_validation'),
    ({'support_atol':1e-3},'request_validation'),
    ({'mode':'unitary'},'request_validation'),
])
def test_stationary_errors(changes,code):
    response=client.post('/api/stationary',json=request(**changes))
    assert response.status_code==422, response.text
    assert response.json()['code']==code


def test_larger_transition_uses_sparse_entries_without_density():
    data=client.post('/api/stationary',json=request(graph={'kind':'complete','size':10},analysis_steps=1)).json()
    assert data['transition_matrix'] is None and data['quantum'] is None
    assert len(data['atom_labels'])==90
    assert len(data['transitions'])==810
