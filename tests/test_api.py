"""HTTP contract and a hand-computed end-to-end example."""
import numpy as np
import pytest
from fastapi.testclient import TestClient

from sqw.api.app import app

client = TestClient(app)


def experiment(**changes):
    payload = {"graph": {"kind": "path", "size": 3}, "preset": "grover", "mode": "unitary", "initial": {"kind": "basis", "edge": [1, 0]}, "steps": 2, "seed": 123}
    payload.update(changes)
    return payload


def test_health_and_graph_basis():
    assert client.get("/api/health").json()["status"] == "ok"
    result = client.post("/api/graph", json={"kind": "path", "size": 3, "preset": "grover"})
    assert result.status_code == 200
    assert result.json()["directed_edges"] == [[0, 1], [1, 0], [1, 2], [2, 1]]
    assert result.json()["neighbors"]["1"] == [0, 2]


@pytest.mark.parametrize("mode", ["unitary", "open", "trajectory"])
def test_path3_exact_transport(mode):
    response = client.post("/api/simulate", json=experiment(mode=mode))
    assert response.status_code == 200, response.text
    result = response.json()
    assert len(result["frames"]) == 3
    np.testing.assert_allclose(result["frames"][0]["edge_probabilities"], [0, 1, 0, 0], atol=1e-12)
    np.testing.assert_allclose(result["frames"][1]["edge_probabilities"], [0, 0, 0, 1], atol=1e-12)
    np.testing.assert_allclose(result["frames"][2]["edge_probabilities"], [0, 0, 1, 0], atol=1e-12)
    if mode == "trajectory":
        assert result["outcomes"] == [1, 2]
        assert result["frames"][0]["measurement"] is None
        assert result["frames"][1]["measurement"] == 1


def test_matrix_round_trip_and_coherent_vs_open():
    graph = client.post("/api/graph", json={"kind": "cycle", "size": 3, "preset": "dft"}).json()
    request = experiment(graph={"kind": "cycle", "size": 3}, scattering=graph["scattering"], initial={"kind": "uniform"}, steps=2)
    closed = client.post("/api/simulate", json=request).json()
    opened = client.post("/api/simulate", json={**request, "mode": "open"}).json()
    assert closed["graph"]["scattering"] == graph["scattering"]
    assert closed["frames"][1]["purity"] == pytest.approx(1)
    assert opened["frames"][1]["purity"] == pytest.approx(1 / 3)


def test_trajectory_reproducibility_and_prefix_for_step_button():
    request = experiment(graph={"kind": "cycle", "size": 3}, preset="dft", mode="trajectory", initial={"kind": "uniform"}, steps=10)
    one = client.post("/api/simulate", json=request).json()
    two = client.post("/api/simulate", json=request).json()
    short = client.post("/api/simulate", json={**request, "steps": 4}).json()
    assert one == two
    assert short["frames"] == one["frames"][:5]


@pytest.mark.parametrize("changes", [
    {"steps": -1}, {"steps": 201}, {"steps": 1.5}, {"mode": "vertex"},
    {"initial": {"kind": "basis", "edge": [0, 2]}},
    {"graph": {"kind": "cycle", "size": 2}},
    {"graph": {"kind": "complete", "size": 32}},
    {"scattering": {}}, {"seed": -1}, {"unknown": True},
])
def test_invalid_requests_rejected(changes):
    response = client.post("/api/simulate", json=experiment(**changes))
    assert response.status_code == 422, response.text
    assert "detail" in response.json()


def test_invalid_local_matrix_rejected_with_vertex_context():
    graph = client.post("/api/graph", json={"kind": "path", "size": 3, "preset": "grover"}).json()
    graph["scattering"]["1"] = [[[2, 0], [0, 0]], [[0, 0], [2, 0]]]
    response = client.post("/api/simulate", json=experiment(scattering=graph["scattering"]))
    assert response.status_code == 422
    assert "1" in response.json()["detail"]


def test_hadamard_dimension_and_random_seed():
    assert client.post("/api/scattering", json={"preset": "hadamard", "degree": 3}).status_code == 422
    request = {"preset": "random", "degree": 3, "seed": 9}
    first = client.post("/api/scattering", json=request)
    assert first.status_code == 200
    assert first.json() == client.post("/api/scattering", json=request).json()


@pytest.mark.parametrize("edge", [[True, 0], [1.0, 0], ["1", 0]])
def test_basis_edge_labels_must_be_actual_integers(edge):
    response = client.post("/api/simulate", json=experiment(initial={"kind": "basis", "edge": edge}))
    assert response.status_code == 422


@pytest.mark.parametrize("token", ["NaN", "Infinity", "-Infinity", "1e999", '"nan"', "true"])
def test_nonfinite_and_non_numeric_matrix_json_returns_validation_error(token):
    payload = (
        '{"graph":{"kind":"path","size":2},"steps":0,'
        '"scattering":{"0":[[[' + token + ',0]]],"1":[[[1,0]]]}}'
    )
    response = client.post("/api/simulate", content=payload, headers={"Content-Type": "application/json"})
    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"][:3] == ["body", "scattering", "0"]


def test_finite_matrix_entries_with_overflowing_unitarity_residual_are_rejected():
    response = client.post("/api/simulate", json={
        "graph": {"kind": "path", "size": 2}, "steps": 0,
        "scattering": {"0": [[[1e308, 1e308]]], "1": [[[1, 0]]]},
    })
    assert response.status_code == 422
    assert "unitary" in response.json()["detail"]


@pytest.mark.parametrize("matrix", [[], [[]], [[[1, 0]], []], [[[1, 0], [0, 0]]]])
def test_empty_ragged_and_wrong_dimension_matrices_are_rejected(matrix):
    response = client.post("/api/simulate", json={
        "graph": {"kind": "path", "size": 2}, "steps": 0,
        "scattering": {"0": matrix, "1": [[[1, 0]]]},
    })
    assert response.status_code == 422


def test_dense_run_budget_is_enforced_before_allocating_history(monkeypatch):
    monkeypatch.setattr("sqw.api.app.MAX_DENSITY_WORK", 32)
    response = client.post("/api/simulate", json=experiment(mode="open", steps=2))
    assert response.status_code == 422
    assert "too large" in response.json()["detail"]
    assert response.json()["code"] == "density_budget"


@pytest.mark.parametrize("changes,code,params", [
    ({"graph": {"kind": "cycle", "size": 2}}, "cycle_size", {}),
    ({"graph": {"kind": "complete", "size": 32}}, "edge_limit", {"limit": 256}),
    ({"scattering": {}}, "matrix_vertices", {}),
    ({"initial": {"kind": "basis", "edge": [0, 2]}}, "invalid_edge", {"target": 0, "source": 2}),
])
def test_error_codes_are_additive_and_language_independent(changes, code, params):
    payload = experiment(**changes)
    english = client.post("/api/simulate", json=payload, headers={"Accept-Language": "en"})
    german = client.post("/api/simulate", json=payload, headers={"Accept-Language": "de"})
    assert english.status_code == german.status_code == 422
    assert english.json() == german.json()
    assert isinstance(english.json()["detail"], str)
    assert english.json()["code"] == code
    assert english.json()["params"] == params


def test_matrix_error_codes_preserve_vertex_and_dimensions():
    graph = client.post("/api/graph", json={"kind": "path", "size": 3, "preset": "grover"}).json()
    graph["scattering"]["1"] = [[[1, 0]]]
    wrong_size = client.post("/api/simulate", json=experiment(scattering=graph["scattering"])).json()
    assert wrong_size["code"] == "matrix_dimension"
    assert wrong_size["params"] == {"vertex": 1, "degree": 2}
    graph["scattering"]["1"] = [[[2, 0], [0, 0]], [[0, 0], [2, 0]]]
    not_unitary = client.post("/api/simulate", json=experiment(scattering=graph["scattering"])).json()
    assert not_unitary["code"] == "matrix_not_unitary"
    assert not_unitary["params"] == {"vertex": 1}
    hadamard = client.post("/api/scattering", json={"preset": "hadamard", "degree": 3}).json()
    assert hadamard["code"] == "hadamard_degree"
    assert hadamard["params"] == {"degree": 3}


def test_request_validation_exposes_safe_translatable_issues():
    result = client.post("/api/simulate", json=experiment(steps=201, seed=-1)).json()
    assert result["code"] == "request_validation"
    assert result["issues"] == [
        {"path": ["body", "steps"], "code": "maximum", "params": {"maximum": 200}},
        {"path": ["body", "seed"], "code": "minimum", "params": {"minimum": 0}},
    ]
    assert all("input" not in detail for detail in result["detail"])


def test_language_header_does_not_change_seeded_simulation():
    request = experiment(graph={"kind": "cycle", "size": 3}, preset="dft", mode="trajectory", initial={"kind": "uniform"}, steps=8)
    english = client.post("/api/simulate", json=request, headers={"Accept-Language": "en"})
    german = client.post("/api/simulate", json=request, headers={"Accept-Language": "de"})
    assert english.status_code == german.status_code == 200
    assert english.json() == german.json()
