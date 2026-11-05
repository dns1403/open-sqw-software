"""Custom inputs use the same ordered graph, quantum and reduced engines."""
import numpy as np
import pytest
from fastapi.testclient import TestClient
from numpy.testing import assert_allclose
from sqw.api.app import app, build_walk, experiment
from sqw.api.schemas import GraphSpec, SimulationRequest
from sqw.api.stationary_cache import stationary_model
from sqw.core import scattering_matrix
from test_markov_api import request, encode

client = TestClient(app)


def custom(graph):
    return {'kind':'custom','size':len(graph['vertices']),
        **{k:graph[k] for k in ('vertices','edges','neighbors')}}


@pytest.mark.parametrize('kind', ['path','cycle','star','complete'])
@pytest.mark.parametrize('mode', ['unitary','open','trajectory','vertex'])
def test_custom_equivalent_to_each_existing_preset_in_every_model(kind,mode):
    graph = client.post('/api/graph',json={'kind':kind,'size':4,'preset':'dft'}).json()
    base = request(graph={'kind':kind,'size':4},mode=mode,preset='dft',scattering=graph['scattering'])
    original = client.post('/api/simulate',json=base)
    edited = client.post('/api/simulate',json={**base,'graph':custom(graph)})
    assert original.status_code==edited.status_code==200,edited.text
    assert edited.json()==original.json()


def path_spec():
    return {'kind':'custom','size':3,'vertices':[2,9,17],
        'edges':[[2,9],[9,17]],'neighbors':{'2':[9],'9':[2,17],'17':[9]}}


def scientific_request():
    return request(graph=path_spec(),initial={'kind':'basis','edge':[9,2]},
        scattering={'2':encode(np.array([[1j]])),'9':encode(scattering_matrix('hadamard',2)),
                    '17':encode(np.array([[np.exp(.3j)]]))},steps=8)


def test_noncontiguous_identifiers_ports_phases_and_custom_unitary_entries():
    req = SimulationRequest(**scientific_request())
    edge,_,_ = experiment(req)
    assert edge.graph.directed_edges == ((2,9),(9,2),(9,17),(17,9))
    matrix = edge.operator.toarray()
    assert_allclose(matrix[:,0],[0,1j,0,0])
    assert_allclose(matrix[:,1],[1/np.sqrt(2),0,0,1/np.sqrt(2)])
    assert_allclose(matrix.conj().T@matrix,np.eye(4),atol=1e-14)
    assert_allclose(scattering_matrix('permutation',7,np.random.default_rng(9)),
        scattering_matrix('permutation',7,np.random.default_rng(9)))


@pytest.mark.parametrize('mode', ['open','vertex'])
def test_custom_reference_and_optimized_full_means_agree(mode):
    payload = scientific_request() | {'mode':mode,'vertex_dynamics':'mean','initial':{'kind':'maximally_mixed'}}
    a = client.post('/api/simulate',json=payload|{'strategy':'reference'}).json()
    b = client.post('/api/simulate',json=payload|{'strategy':'optimized'}).json()
    for x,y in zip(a['frames'],b['frames']):
        assert_allclose(x['vertex_probabilities'],y['vertex_probabilities'],atol=2e-13)
        assert_allclose(x['purity'],y['purity'],atol=2e-13)


@pytest.mark.parametrize('route,extra', [('analysis',{}),('stationary',{'analysis_steps':12}),
    ('statistics',{'samples':30}),('ensemble',{'trajectories':40})])
def test_all_research_routes_accept_custom_graphs(route,extra):
    response = client.post('/api/'+route,json=scientific_request()|extra)
    assert response.status_code==200,response.text
    if route in ('analysis','stationary','statistics'):
        assert response.json()['atom_labels']==[[2,9],[9,2],[9,17],[17,9]]


@pytest.mark.parametrize('mutation', ['loop','duplicate','disconnected','unknown','ports','missing','size'])
def test_invalid_graphs_and_port_reinterpretations_rejected(mutation):
    spec=path_spec()
    if mutation=='loop': spec['edges'].append([2,2])
    if mutation=='duplicate': spec['edges'].append([9,2])
    if mutation=='disconnected': spec['edges']=[[2,9]]
    if mutation=='unknown': spec['edges'].append([2,99])
    if mutation=='ports': spec['neighbors']['9']=[17,2]
    if mutation=='missing': del spec['neighbors']
    if mutation=='size': spec['size']=4
    assert client.post('/api/graph',json=spec).status_code==422


def document():
    return {'format':'sqw-experiment','version':1,'experiment':scientific_request(),
        'vertices':[{'id':x,'label':label,'position':[40.+100*i,120.]} for i,(x,label) in enumerate(zip([2,9,17],['A','B','C']))],
        'matrix_presets':{'2':None,'9':'hadamard','17':None}}


def test_document_validation_round_trip_preserves_physics_positions_and_complex_entries():
    doc=document()
    response=client.post('/api/experiments/validate',json=doc)
    assert response.status_code==200,response.text
    restored=response.json()['document']
    assert restored['vertices']==doc['vertices']
    assert restored['experiment']['scattering']==doc['experiment']['scattering']
    assert restored['experiment']['graph']['neighbors']==doc['experiment']['graph']['neighbors']
    assert client.post('/api/simulate',json=restored['experiment']).json()==client.post('/api/simulate',json=doc['experiment']).json()


@pytest.mark.parametrize('mutation', ['version','boolean_version','labels','ids','positions','matrix','omega','initial','extra'])
def test_malformed_imports_rejected_without_repair(mutation):
    doc=document()
    if mutation=='version': doc['version']=2
    if mutation=='boolean_version': doc['version']=True
    if mutation=='labels': doc['vertices'][0]['label']=' '
    if mutation=='ids': doc['vertices'][1]['id']=2
    if mutation=='positions': doc['vertices'][0]['position']=[0,'NaN']
    if mutation=='matrix': doc['experiment']['scattering']['2']=[[[2,0]]]
    if mutation=='omega': doc['experiment']['vertex_parameters']={'omega':{'2':[[1,0]]}}
    if mutation=='initial': doc['experiment']['initial']={'kind':'pure','vector':[[1,0]]}
    if mutation=='extra': doc['surprise']='not part of this format'
    response=client.post('/api/experiments/validate',json=doc)
    assert response.status_code==422,response.text


def test_structure_and_matrix_edits_invalidate_cached_markov_operators():
    req=SimulationRequest(**scientific_request()); a,_,_=experiment(req)
    first=stationary_model(a)
    assert stationary_model(a) is first
    req.scattering['9']=encode(np.eye(2,dtype=complex)); b,_,_=experiment(req)
    assert stationary_model(b).chain is not first.chain
    spec=path_spec(); spec['edges'].append([2,17]); spec['neighbors']={'2':[9,17],'9':[2,17],'17':[2,9]}
    changed=build_walk(GraphSpec(**spec),'dft',42)
    assert stationary_model(changed).chain is not first.chain

@pytest.mark.parametrize('matrix', [np.array([[1j]]),np.array([[np.exp(.345j)]]),scattering_matrix('random',5,np.random.default_rng(19))])
def test_individual_matrix_validation_preserves_arbitrary_complex_unitary(matrix):
    response=client.post('/api/scattering/validate',json={'degree':len(matrix),'matrix':encode(matrix)})
    assert response.status_code==200,response.text
    assert response.json()['matrix']==encode(matrix)
    assert response.json()['residual']<=1e-10


@pytest.mark.parametrize('degree,matrix', [(2,[[[1,0]]]),(1,[[[1.01,0]]]),(1,[[[1e308,0]]]),(1,[[['NaN',0]]]),(0,[])])
def test_individual_matrix_validation_rejects_invalid_input_without_projection(degree,matrix):
    response=client.post('/api/scattering/validate',json={'degree':degree,'matrix':matrix})
    assert response.status_code==422,response.text


@pytest.mark.parametrize('mode', ['unitary','open','trajectory','vertex'])
@pytest.mark.parametrize('kind', ['pure','mixed'])
def test_custom_initial_states_and_document_roundtrip_in_all_models(mode,kind):
    dimension=3 if mode=='vertex' else 4
    vector=np.arange(1,dimension+1,dtype=complex)*np.exp(1j*np.arange(dimension))
    vector/=np.linalg.norm(vector)
    rho=.8*np.outer(vector,vector.conj())+.2*np.eye(dimension)/dimension
    initial={'kind':kind,**({'vector':encode(vector)} if kind=='pure' else {'density':encode(rho)})}
    doc=document()
    doc['experiment'].update(mode=mode,initial=initial)
    validated=client.post('/api/experiments/validate',json=doc)
    assert validated.status_code==200,validated.text
    before=client.post('/api/simulate',json=doc['experiment'])
    after=client.post('/api/simulate',json=validated.json()['document']['experiment'])
    assert before.status_code==after.status_code==200,after.text
    assert before.json()==after.json()
