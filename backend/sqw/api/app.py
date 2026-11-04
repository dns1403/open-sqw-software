"""Stateless, local HTTP adapter for the scientific core."""
import numpy as np
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from sqw.core import (
    GraphModel, ReferenceTrajectory, ScatteringWalk, basis_state,
    density_from_state, scattering_matrix, uniform_state, validate_scattering,
)
from .errors import RequestProblem, client_error, validation_issue
from .schemas import (
    Frame, GraphRequest, GraphResponse, ScatteringRequest,
    SimulationRequest, SimulationResponse,
)

app = FastAPI(title="Scattering Quantum Walk Lab", version="0.1.0")


@app.exception_handler(RequestValidationError)
async def invalid_request(_request, error: RequestValidationError):
    # Pydantic includes the rejected input in errors. JSON may decode exponent
    # overflow or nonstandard NaN/Infinity into nonfinite floats, which cannot
    # themselves be serialized by JSONResponse. Return useful locations and
    # messages without reflecting the malformed value into the response.
    details = [
        {"loc": item["loc"], "msg": item["msg"], "type": item["type"]}
        for item in error.errors()
    ]
    return JSONResponse(status_code=422, content={
        "detail": details, "code": "request_validation", "params": {},
        "issues": [validation_issue(item) for item in error.errors()],
    })

# Limits protect the local interactive reference implementation. Core has no
# arbitrary graph-size limit and does not construct dense superoperators.
MAX_EDGE_DIMENSION = 256
MAX_DENSITY_WORK = 12_000_000


def encode_matrix(matrix: np.ndarray) -> list:
    return np.stack((matrix.real, matrix.imag), axis=-1).tolist()


def preset_matrix(preset, degree, rng, vertex=None):
    if preset == "hadamard" and degree != 2:
        raise RequestProblem(
            "hadamard_degree", "Hadamard scattering is defined only at vertices of degree 2.",
            degree=degree,
        )
    return scattering_matrix(preset, degree, rng=rng)


def build_walk(spec, preset, seed, supplied=None) -> ScatteringWalk:
    if spec.kind == "cycle" and spec.size < 3:
        raise RequestProblem("cycle_size", "A simple cycle requires at least 3 vertices.")
    graph = GraphModel.preset(spec.kind, spec.size)
    if graph.dimension > MAX_EDGE_DIMENSION:
        raise RequestProblem("edge_limit", f"Interactive API supports at most {MAX_EDGE_DIMENSION} directed edges; use the Python core for larger graphs.", limit=MAX_EDGE_DIMENSION)
    if supplied is None:
        rng = np.random.default_rng(seed)
        matrices = {x: preset_matrix(preset, len(graph.neighbors[x]), rng, x) for x in graph.vertices}
    else:
        expected = {str(x) for x in graph.vertices}
        if set(supplied) != expected:
            raise RequestProblem("matrix_vertices", "Scattering matrices must be provided for exactly all vertices, using their canonical string labels.")
        matrices = {}
        for x in graph.vertices:
            try:
                data = np.asarray(supplied[str(x)], dtype=float)
            except (ValueError, TypeError) as error:
                raise RequestProblem("matrix_shape", f"Matrix at vertex {x} must contain rows of [real, imaginary] pairs.", vertex=x) from error
            if data.ndim != 3 or data.shape[-1] != 2:
                raise RequestProblem("matrix_shape", f"Matrix at vertex {x} must contain rows of [real, imaginary] pairs.", vertex=x)
            degree = graph.degree(x)
            if data.shape[:2] != (degree, degree):
                raise RequestProblem("matrix_dimension", f"Vertex {x}: Scattering matrix must have shape ({degree}, {degree}); received {data.shape[:2]}.", vertex=x, degree=degree)
            matrices[x] = data[..., 0] + 1j * data[..., 1]
            try:
                validate_scattering(matrices[x], degree)
            except ValueError as error:
                raise RequestProblem("matrix_not_unitary", f"Vertex {x}: {error}", vertex=x) from error
    return ScatteringWalk(graph, matrices)


def describe(walk: ScatteringWalk) -> GraphResponse:
    g = walk.graph
    return GraphResponse(
        vertices=list(g.vertices), edges=list(g.edges),
        directed_edges=list(g.directed_edges),
        neighbors={str(x): list(g.neighbors[x]) for x in g.vertices},
        scattering={str(x): encode_matrix(walk.scattering[x]) for x in g.vertices},
        dimension=g.dimension,
    )


def frame(walk, state, step, measurement=None, probabilities=None) -> Frame:
    pure = state.ndim == 1
    norm = float(np.vdot(state, state).real) if pure else float(np.trace(state).real)
    purity = norm**2 if pure else float(np.vdot(state, state).real)
    return Frame(
        step=step, edge_probabilities=walk.edge_probabilities(state).tolist(),
        vertex_probabilities=walk.vertex_probabilities(state).tolist(),
        trace=norm, purity=purity, measurement=measurement,
        measurement_probability=(None if probabilities is None else float(probabilities[walk.graph.vertices.index(measurement)])),
        measurement_probabilities=None if probabilities is None else probabilities.tolist(),
    )


@app.get("/api/health")
def health():
    return {"status": "ok", "version": "0.1.0"}


@app.post("/api/graph", response_model=GraphResponse)
def graph_endpoint(request: GraphRequest):
    try:
        return describe(build_walk(request, request.preset, request.seed))
    except (ValueError, TypeError) as error:
        return client_error(error)


@app.post("/api/scattering")
def scattering_endpoint(request: ScatteringRequest):
    try:
        matrix = preset_matrix(request.preset, request.degree, np.random.default_rng(request.seed))
        return {"matrix": encode_matrix(matrix)}
    except (ValueError, TypeError) as error:
        return client_error(error)


@app.post("/api/simulate", response_model=SimulationResponse)
def simulate(request: SimulationRequest):
    try:
        walk = build_walk(request.graph, request.preset, request.seed, request.scattering)
        if request.mode == "open" and walk.graph.dimension**2 * (request.steps + 1) > MAX_DENSITY_WORK:
            raise RequestProblem("density_budget", "This dense reference run is too large for the interactive API. Reduce graph size or step count, or use the Python core.")
        if request.initial.kind == "uniform":
            initial = uniform_state(walk.graph)
        else:
            edge = request.initial.edge or walk.graph.directed_edges[0]
            if edge not in walk.graph.edge_index:
                raise RequestProblem("invalid_edge", f"{edge!r} is not a directed edge (target, source) of this graph.", target=edge[0], source=edge[1])
            initial = basis_state(walk.graph, edge)
        outcomes = []
        if request.mode == "trajectory":
            trajectory = ReferenceTrajectory(walk, seed=request.seed).run(initial, request.steps)
            outcomes = list(trajectory.outcomes)
            frames = [frame(walk, trajectory.states[0], 0)]
            frames.extend(frame(walk, state, t, outcomes[t - 1], trajectory.probabilities[t - 1]) for t, state in enumerate(trajectory.states[1:], 1))
        else:
            state = density_from_state(initial) if request.mode == "open" else initial
            frames = [frame(walk, state, 0)]
            advance = walk.step_density if request.mode == "open" else walk.step_pure
            for t in range(1, request.steps + 1):
                state = advance(state)
                frames.append(frame(walk, state, t))
        return SimulationResponse(graph=describe(walk), mode=request.mode, frames=frames, outcomes=outcomes)
    except (ValueError, TypeError, KeyError) as error:
        return client_error(error)
