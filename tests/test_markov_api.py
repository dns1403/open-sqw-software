"""API orientations, stages, arbitrary states and independent strategies."""
import numpy as np
import pytest
from fastapi.testclient import TestClient
from numpy.testing import assert_allclose
from sqw.api.app import app
from test_edge_markov import initial_state

client = TestClient(app)


def encode(array):
    return np.stack((array.real, array.imag), axis=-1).tolist()


def request(**changes):
    return {"graph": {"kind": "cycle", "size": 3}, "preset": "random", "seed": 91,
            "mode": "trajectory", "strategy": "optimized", "steps": 4,
            "initial": {"kind": "uniform"}, **changes}


@pytest.mark.parametrize("mode,vertex_dynamics", [("open", "trajectory"), ("vertex", "mean")])
@pytest.mark.parametrize("mixed", [False, True])
def test_averaged_strategy_equivalence_and_custom_complex_states(mode, vertex_dynamics, mixed):
    dimension = 3 if mode == "vertex" else 6
    state = initial_state(dimension, mixed)
    initial = {"kind": "mixed", "density": encode(state)} if mixed else {"kind": "pure", "vector": encode(state)}
    payload = request(mode=mode, vertex_dynamics=vertex_dynamics, initial=initial)
    optimized = client.post("/api/simulate", json=payload)
    reference = client.post("/api/simulate", json={**payload, "strategy": "reference"})
    assert optimized.status_code == reference.status_code == 200, optimized.text
    a, b = optimized.json(), reference.json()
    for f, g in zip(a["frames"], b["frames"]):
        for key in ["vertex_probabilities", "edge_probabilities", "purity", "trace"]:
            assert_allclose(f[key], g[key], atol=3e-12, rtol=0)
        assert f["state_kind"] == "mean"
        if f["step"] >= (1 if mode == "vertex" else 2):
            assert sum(f["state_weights"]) == pytest.approx(1)


@pytest.mark.parametrize("mode", ["trajectory", "vertex"])
@pytest.mark.parametrize("strategy", ["reference", "optimized"])
def test_trajectory_prefix_and_stage_metadata(mode, strategy):
    payload = request(mode=mode, strategy=strategy, initial={"kind": "maximally_mixed"})
    full = client.post("/api/simulate", json=payload).json()
    for n in (0, 1, 2, 3):
        prefix = client.post("/api/simulate", json={**payload, "steps": n}).json()
        assert prefix["outcomes"] == full["outcomes"][:n]
        assert prefix["frames"] == full["frames"][:n + 1]
    assert full["frames"][0]["stage"] == "initial"
    assert full["frames"][1]["stage"] == ("vertex_atom" if mode == "vertex" else "first_scattering")
    assert full["frames"][2]["atom_id"] is not None
    assert full["frames"][2]["purity"] == pytest.approx(1)
    if mode == "vertex": assert full["frames"][0]["edge_probabilities"] == []


@pytest.mark.parametrize("mode", ["trajectory", "vertex"])
def test_markov_inspection_orientation_and_complex_reconstruction(mode):
    response = client.post("/api/analysis", json=request(mode=mode, atom_id=1))
    assert response.status_code == 200, response.text
    data = response.json()
    matrix = np.array(data["transition_matrix"])
    assert data["orientation"] == ("row" if mode == "vertex" else "column")
    assert_allclose(matrix[1] if mode == "vertex" else matrix[:, 1], data["next_atom_probabilities"])
    ket = np.array(data["atom_ket"]) @ [1, 1j]
    assert np.linalg.norm(ket) == pytest.approx(1)
    for key in ("current_density", "after_measurement_density"):
        rho = np.array(data[key]) @ [1, 1j]
        assert_allclose(np.trace(rho), 1, atol=1e-12)
        assert_allclose(rho, rho.conj().T, atol=1e-12)


def test_vertex_complex_omega_beta_api():
    omega = {str(i): encode(np.array([1, 1j]) / np.sqrt(2)) for i in range(3)}
    a = client.post("/api/analysis", json=request(mode="vertex", vertex_parameters={"omega": omega})).json()
    b = client.post("/api/analysis", json=request(mode="vertex", vertex_parameters={"omega": omega, "beta": {"0": .4, "1": .8, "2": -.1}})).json()
    assert_allclose(a["transition_matrix"], b["transition_matrix"], atol=1e-14)
    assert not np.allclose(a["atom_ket"], b["atom_ket"])


@pytest.mark.parametrize("mode", ["trajectory", "vertex"])
def test_ensemble_endpoint_statistics_and_language_independence(mode):
    payload = request(mode=mode, trajectories=120, selected_histories=2, steps=3)
    a = client.post("/api/ensemble", json=payload, headers={"Accept-Language": "en"})
    b = client.post("/api/ensemble", json=payload, headers={"Accept-Language": "de"})
    assert a.status_code == b.status_code == 200, a.text
    assert a.json() == b.json()
    result = a.json()
    assert sum(result["frames"][-1]["state_counts"]) == 120
    assert len(result["selected_outcomes"]) == 2
    assert result["frames"][-1]["born_vertex_total_variation"] >= 0


@pytest.mark.parametrize("route,changes,code", [
    ("simulate", {"initial": {"kind": "pure", "vector": [[1, 0]]}}, "initial_state"),
    ("simulate", {"mode": "vertex", "vertex_parameters": {"omega": {"0": [[1, 0]]}}}, "vertex_parameters"),
    ("analysis", {"atom_id": 90}, "atom_id"),
    ("ensemble", {"trajectories": 100000, "steps": 200}, "ensemble_budget"),
    ("ensemble", {"trajectories": 1, "selected_histories": 3}, "ensemble_histories"),
    ("simulate", {"strategy": "unsupported"}, "request_validation"),
])
def test_new_errors_have_stable_translatable_codes(route, changes, code):
    response = client.post(f"/api/{route}", json=request(**changes))
    assert response.status_code == 422, response.text
    assert response.json()["code"] == code
