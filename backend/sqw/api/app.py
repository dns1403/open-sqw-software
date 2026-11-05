"""Stateless, local HTTP adapter for the scientific core."""
import numpy as np
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from sqw.core import (
    GraphModel, ReferenceTrajectory, ScatteringWalk, basis_state,
    density_from_state, scattering_matrix, uniform_state, validate_scattering, validate_state,
    InducedVertexWalk, EdgeReduction, VertexReduction, OptimizedEdgeTrajectory,
    OptimizedVertexTrajectory, ReferenceVertexTrajectory, run_ensemble,
)
from .errors import RequestProblem, client_error, validation_issue
from .schemas import (
    Frame, GraphRequest, GraphResponse, ScatteringRequest, ScatteringValidationRequest,
    SimulationRequest, SimulationResponse, EnsembleRequest, AnalysisRequest, StationaryRequest, StatisticsRequest, ExperimentDocument,
)
from .stationary_cache import stationary_model
from .statistics_cache import statistics_model

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
    if spec.kind == 'custom':
        try:
            graph = GraphModel.from_edges(spec.vertices, spec.edges)
        except ValueError as error:
            raise RequestProblem('custom_graph', str(error)) from error
        expected_ports = {str(x): list(graph.neighbors[x]) for x in graph.vertices}
        if spec.neighbors != expected_ports:
            raise RequestProblem('graph_ports', 'Neighbor ordering must explicitly match ascending stable vertex IDs. No matrix is silently permuted.')
    else:
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


@app.post('/api/experiments/validate')
def validate_experiment_document(document: ExperimentDocument):
    """Validate the complete imported experiment before the browser replaces state."""
    try:
        request = document.experiment
        if request.graph.kind != 'custom' or request.scattering is None:
            raise RequestProblem('experiment_document', 'Saved experiments require an explicit custom graph and every scattering matrix.')
        edge, walk, initial = experiment(request)
        ids = [v.id for v in document.vertices]
        if len(set(ids)) != len(ids) or set(ids) != set(edge.graph.vertices):
            raise RequestProblem('experiment_document', 'Presentation vertices must match the graph exactly.')
        if any(not v.label.strip() for v in document.vertices) or set(document.matrix_presets) != {str(x) for x in ids}:
            raise RequestProblem('experiment_document', 'Each vertex needs a display label and a matrix preset or null.')
        # Vertex parameters remain scientific data even when importing Edge mode.
        if request.mode != 'vertex' and (request.vertex_parameters.omega is not None or request.vertex_parameters.beta is not None):
            params = request.vertex_parameters
            InducedVertexWalk(edge,
                None if params.omega is None else {int(x):decode_complex(v) for x,v in params.omega.items()},
                None if params.beta is None else {int(x):v for x,v in params.beta.items()})
        return {'document': document.model_dump(), 'graph': describe(edge)}
    except (ValueError, TypeError, KeyError) as error:
        return client_error(error if isinstance(error, RequestProblem) else RequestProblem('experiment_document', str(error)))


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


def decode_complex(data):
    array = np.asarray(data, dtype=float)
    if array.ndim < 2 or array.shape[-1] != 2:
        raise ValueError("Complex values must be [real, imaginary] pairs.")
    return array[..., 0] + 1j * array[..., 1]


@app.post('/api/scattering/validate')
def validate_matrix(request: ScatteringValidationRequest):
    try:
        matrix = validate_scattering(decode_complex(request.matrix), request.degree)
        return {'matrix': encode_matrix(matrix),
                'residual': float(np.max(abs(matrix.conj().T @ matrix - np.eye(request.degree))))}
    except (ValueError, TypeError) as error:
        return client_error(RequestProblem('custom_matrix', str(error)))


def experiment(request):
    edge = build_walk(request.graph, request.preset, request.seed, request.scattering)
    vertex = request.mode == "vertex"
    walk = edge
    if vertex:
        params = request.vertex_parameters
        try:
            omega = None if params.omega is None else {int(x): decode_complex(v) for x, v in params.omega.items()}
            beta = None if params.beta is None else {int(x): v for x, v in params.beta.items()}
            walk = InducedVertexWalk(edge, omega, beta)
        except (ValueError, TypeError) as error:
            raise RequestProblem("vertex_parameters", str(error)) from error
    d = walk.dimension if vertex else edge.graph.dimension
    spec = request.initial
    try:
        if spec.kind == "uniform":
            state = np.ones(d, complex) / np.sqrt(d)
        elif spec.kind == "maximally_mixed":
            state = np.eye(d, dtype=complex) / d
        elif spec.kind == "pure":
            state = decode_complex(spec.vector)
            if state.ndim != 1: raise ValueError("Expected a pure vector.")
        elif spec.kind == "mixed":
            state = decode_complex(spec.density)
            if state.ndim != 2: raise ValueError("Expected a density matrix.")
        elif vertex:
            label = edge.graph.vertices[0] if spec.vertex is None else spec.vertex
            if label not in edge.graph.vertex_index: raise ValueError("Unknown initial vertex.")
            state = np.zeros(d, complex); state[edge.graph.vertex_index[label]] = 1
        else:
            pair = spec.edge or edge.graph.directed_edges[0]
            if pair not in edge.graph.edge_index:
                raise RequestProblem("invalid_edge", f"{pair!r} is not a directed edge (target, source) of this graph.", target=pair[0], source=pair[1])
            state = basis_state(edge.graph, pair)
        state = validate_state(state, d)
    except RequestProblem:
        raise
    except (ValueError, TypeError) as error:
        raise RequestProblem("initial_state", str(error)) from error
    return edge, walk, state


def reference_frame(walk, state, step, *, vertex=False, measurement=None, probabilities=None, state_kind="conditional", outcomes=()):
    if not vertex:
        result = frame(walk, state, step, measurement, probabilities)
    else:
        diagonal = abs(state) ** 2 if state.ndim == 1 else np.diag(state).real
        result = Frame(step=step, edge_probabilities=[], vertex_probabilities=diagonal.tolist(),
            trace=float(np.vdot(state, state).real if state.ndim == 1 else np.trace(state).real),
            purity=1.0 if state.ndim == 1 else float(np.vdot(state, state).real),
            measurement=measurement, measurement_probability=None if probabilities is None else float(probabilities[walk.graph.vertex_index[measurement]]),
            measurement_probabilities=None if probabilities is None else probabilities.tolist())
    result.state_kind = state_kind
    result.stage = "initial" if step == 0 else "mean" if state_kind == "mean" else "unitary" if state_kind == "unitary" else "vertex_atom" if vertex else "first_scattering" if step == 1 else "edge_atom"
    if state_kind == "conditional" and step >= (1 if vertex else 2):
        if vertex:
            result.atom_id = walk.graph.vertex_index[measurement]
            result.atom_vertex = measurement
        else:
            result.atom_edge = (outcomes[step - 1], outcomes[step - 2])
            result.atom_id = walk.graph.edge_index[result.atom_edge]
    return result


def compact_frame(state, *, vertex=False, previous=None, state_kind="conditional"):
    weights = getattr(state, "label_weights" if vertex else "atom_weights", None)
    measurement = getattr(state, "outcome", None)
    atom = None if state_kind != "conditional" else (state.model.graph.vertex_index[measurement] if vertex and state.step else getattr(state, "atom_id", None))
    return Frame(step=state.step, edge_probabilities=[] if vertex else state.born_edges().tolist(),
        vertex_probabilities=state.born_vertices().tolist(), trace=1.0, purity=state.purity(),
        measurement=measurement, measurement_probability=getattr(state, "selected_probability", None),
        measurement_probabilities=None if previous is None else previous.born_vertices().tolist(),
        stage="initial" if state.step == 0 else "mean" if state_kind == "mean" else state.stage,
        state_kind=state_kind, atom_id=atom,
        atom_edge=state.model.graph.directed_edges[atom] if atom is not None and not vertex else None,
        atom_vertex=measurement if vertex and atom is not None else None,
        state_weights=None if weights is None else weights.tolist())


def simulate_experiment(request, *, inspect_last=False):
    edge, walk, initial = experiment(request)
    vertex = request.mode == "vertex"
    conditional = request.mode == "trajectory" or (vertex and request.vertex_dynamics == "trajectory")
    mean = request.mode == "open" or (vertex and not conditional)
    d = walk.dimension if vertex else edge.graph.dimension
    dense_reference = (mean or initial.ndim == 2) and (request.strategy == "reference" or request.mode == "unitary")
    if dense_reference and d**2 * (request.steps + 1) > MAX_DENSITY_WORK:
        raise RequestProblem("density_budget", "This dense reference run is too large for the interactive API. Reduce graph size or step count, or use the Python core.")
    outcomes, last, reduced = [], None, None
    if request.mode == "unitary":
        states = walk.evolve_pure(initial, request.steps) if initial.ndim == 1 else None
        if states is None:
            states = [initial]
            for _ in range(request.steps): states.append(walk.step_unitary_density(states[-1]))
        frames = [reference_frame(walk, state, n, state_kind="unitary") for n, state in enumerate(states)]
        last = states[-1]
    elif request.strategy == "optimized":
        model = VertexReduction(walk) if vertex else EdgeReduction(walk)
        if conditional:
            engine = OptimizedVertexTrajectory(model, seed=request.seed) if vertex else OptimizedEdgeTrajectory(model, seed=request.seed)
            path = engine.run(initial, request.steps)
            outcomes = list(path.outcomes)
            frames = [compact_frame(s, vertex=vertex, previous=path.states[n - 1] if n else None) for n, s in enumerate(path.states)]
            if inspect_last:
                last = path.states[-1].density()
                reduced = path.states[-1].reduced_density() if request.steps else None
        else:
            states = list(model.iter_mean(initial, request.steps))
            frames = [compact_frame(s, vertex=vertex, state_kind="mean") for s in states]
            if inspect_last: last = states[-1].density()
    elif conditional:
        engine = ReferenceVertexTrajectory(walk, seed=request.seed) if vertex else ReferenceTrajectory(walk, seed=request.seed)
        path = engine.run(initial, request.steps)
        outcomes = list(path.outcomes)
        frames = [reference_frame(walk, s, n, vertex=vertex,
            measurement=outcomes[n - 1] if n else None, probabilities=path.probabilities[n - 1] if n else None,
            outcomes=outcomes) for n, s in enumerate(path.states)]
        if inspect_last:
            last = path.states[-1]
            reduced = path.reduced_states[-1] if request.steps else None
    else:
        state = density_from_state(initial) if initial.ndim == 1 else initial
        frames = [reference_frame(walk, state, 0, vertex=vertex, state_kind="mean")]
        for n in range(1, request.steps + 1):
            state = walk.apply_channel(state)
            frames.append(reference_frame(walk, state, n, vertex=vertex, state_kind="mean"))
        if inspect_last: last = state
    response = SimulationResponse(graph=describe(edge), mode=request.mode, frames=frames, outcomes=outcomes,
        strategy="reference" if request.mode == "unitary" else request.strategy, model="vertex" if vertex else "edge")
    return response, walk, last, reduced


@app.post("/api/simulate", response_model=SimulationResponse)
def simulate(request: SimulationRequest):
    try:
        return simulate_experiment(request)[0]
    except (ValueError, TypeError, KeyError) as error:
        return client_error(error)


def json_arrays(value):
    """Serialize result dataclasses and numerical arrays at the API boundary."""
    from dataclasses import fields, is_dataclass
    if isinstance(value, np.ndarray): return value.tolist()
    if isinstance(value, np.generic): return value.item()
    if is_dataclass(value): return {f.name: json_arrays(getattr(value, f.name)) for f in fields(value)}
    if isinstance(value, dict): return {k: json_arrays(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)): return [json_arrays(v) for v in value]
    return value


@app.post("/api/ensemble")
def ensemble(request: EnsembleRequest):
    try:
        edge, walk, initial = experiment(request)
        d = walk.dimension if request.mode == "vertex" else walk.graph.dimension
        work = request.trajectories * max(1, request.steps)
        if work > 10_000_000 or (request.strategy == "reference" and work * d**2 > 50_000_000):
            raise RequestProblem("ensemble_budget", "Requested ensemble exceeds the local interactive work budget.")
        if request.selected_histories > request.trajectories:
            raise RequestProblem("ensemble_histories", "Selected history count exceeds trajectory count.")
        result = run_ensemble(walk, initial, request.trajectories, request.steps, seed=request.seed,
            strategy=request.strategy, statistics=request.statistics, selected_histories=request.selected_histories)
        return json_arrays(result)
    except (ValueError, TypeError, KeyError) as error:
        return client_error(error)


@app.post("/api/analysis")
def analysis(request: AnalysisRequest):
    try:
        edge, selected_walk, _ = experiment(request)
        diagnostic_dimension = selected_walk.dimension if request.mode == "vertex" else edge.graph.dimension
        if diagnostic_dimension > 64:
            raise RequestProblem("analysis_budget", "Dense state/transition inspection is limited to dimension 64; use the Python API for larger diagnostics.")
        result, walk, current, reduced = simulate_experiment(request, inspect_last=True)
        vertex = request.mode == "vertex"
        model = VertexReduction(walk) if vertex else EdgeReduction(walk)
        atom = request.atom_id
        if atom >= model.dimension:
            raise RequestProblem("atom_id", "Atom ID is outside the model basis.")
        label = model.graph.vertices[atom] if vertex else atom
        matrix = model.transition_matrix()
        ket = model.atom_ket(label)
        rho = density_from_state(current) if current.ndim == 1 else current
        projected = None if reduced is None else density_from_state(reduced) if reduced.ndim == 1 else reduced
        return {"model": result.model, "orientation": "row" if vertex else "column",
            "state_step": request.steps, "stage": result.frames[-1].stage,
            "current_density": encode_matrix(rho), "after_measurement_density": None if projected is None else encode_matrix(projected),
            "atom_id": atom, "atom_labels": list(model.graph.vertices) if vertex else list(model.graph.directed_edges),
            "atom_ket": encode_matrix(ket), "transition_matrix": matrix.tolist(),
            "next_atom_probabilities": (matrix[atom] if vertex else matrix[:, atom]).tolist(),
            "eligible": model.eligibility.eligible, "assumptions": "SIMPLE_STATIC" if not vertex else "STATIC_RANK_ONE_PREPARATION"}
    except (ValueError, TypeError, KeyError) as error:
        return client_error(error)


@app.post("/api/stationary")
def stationary(request: StationaryRequest):
    try:
        edge, walk, initial = experiment(request)
        vertex = request.mode == 'vertex'
        d = walk.dimension if vertex else edge.graph.dimension
        if d * (request.analysis_steps + 1) > 250_000:
            raise RequestProblem('stationary_budget', 'Requested stationary-analysis history exceeds 250000 state-time entries.')
        if request.include_density and d > 64:
            raise RequestProblem('analysis_budget', 'Dense stationary state inspection is limited to dimension 64.')
        model = stationary_model(edge, walk if vertex else None, support_atol=request.support_atol)
        chain = model.chain
        if request.stationary_class is not None and request.stationary_class >= len(chain.closed_classes):
            raise RequestProblem('stationary_class', 'Selected recurrent class does not exist.')
        q = model.initial_law(initial)
        mixture = chain.mixture(q)
        frames = tuple(chain.evolve(q, request.analysis_steps, start_step=model.start_step))
        raw, effective = chain.raw_transition, chain.transition
        coo = raw.tocoo()
        transitions = [{'source': int(i), 'target': int(j), 'probability': float(p),
                        'analysis_probability': float(effective[i, j])}
                       for i, j, p in zip(coo.row, coo.col, coo.data)]
        quantum = None
        if request.include_density:
            rho = model.stationary_density(initial, class_index=request.stationary_class)
            quantum = {'density': encode_matrix(rho), 'trace': float(np.trace(rho).real),
                'purity': float(np.vdot(rho, rho).real),
                'channel_residual': float(np.max(abs(walk.apply_channel(rho) - rho))),
                'weights': model.stationary_weights(initial, class_index=request.stationary_class).tolist(),
                'class_index': request.stationary_class}
        result = {
            'model': 'vertex' if vertex else 'edge', 'orientation': model.orientation,
            'start_step': model.start_step, 'analysis_steps': request.analysis_steps,
            'atom_labels': list(edge.graph.vertices) if vertex else list(edge.graph.directed_edges),
            'classes': chain.classes, 'closed_class_ids': [c.id for c in chain.closed_classes],
            'membership': chain.membership, 'transient_states': chain.transient_states,
            'stationary_family': chain.stationary_basis.toarray(), 'absorption': chain.absorption.toarray(),
            'initial_law': q, 'class_weights': mixture.class_weights,
            'stationary_mixture': mixture.stationary, 'irreducible': chain.irreducible,
            'unique_stationary': chain.unique_stationary, 'bistochastic': chain.bistochastic,
            'ordinary_for_all_initials': chain.ordinary_for_all_initials,
            'ordinary_guaranteed': mixture.ordinary_guaranteed,
            'reachable_periods': mixture.reachable_periods,
            'support': {'source': model.support_source, 'policy': chain.support_policy,
                'tolerance': chain.support_atol, 'discarded_entries': chain.discarded_entries,
                'discarded_max_probability': chain.discarded_max_probability,
                'discarded_max_row_mass': chain.discarded_max_row_mass,
                'matrix_change_max_row_l1': chain.matrix_change_max_row_l1},
            'diagnostics': {'row_residual': chain.row_residual, 'column_residual': chain.column_residual,
                'absorption_residual': chain.absorption_residual,
                'absorption_raw_residual': chain.absorption_raw_residual},
            'transitions': transitions,
            # Display in the original model orientation, not the internal row adapter.
            'transition_matrix': (raw.toarray() if vertex else raw.T.toarray()) if d <= 64 else None,
            'frames': frames, 'quantum': quantum,
        }
        return json_arrays(result)
    except (ValueError, TypeError, KeyError) as error:
        return client_error(error)


@app.post('/api/statistics')
def statistics(request: StatisticsRequest):
    try:
        edge, walk, initial = experiment(request)
        vertex = request.mode == 'vertex'
        d = walk.dimension if vertex else edge.graph.dimension
        if d * (request.samples + request.burn_in) > 5_000_000:
            raise RequestProblem('statistics_budget', 'Requested trajectory exceeds the local statistics work budget.')
        if request.observable.kind in ('quantum','coherence_real','coherence_imag') and d > 64:
            raise RequestProblem('statistics_observable_budget', 'Dense Hermitian observable inspection is limited to dimension 64.')
        engine = statistics_model(edge, walk if vertex else None, support_atol=request.support_atol)
        chain = engine.stationary.chain
        if request.stationary_class >= len(chain.closed_classes):
            raise RequestProblem('stationary_class', 'Selected recurrent class does not exist.')
        spec = request.observable.model_dump()
        if spec['matrix'] is not None: spec['matrix'] = decode_complex(spec['matrix'])
        try:
            f = engine.observable(**spec)
        except (ValueError, TypeError, IndexError) as error:
            raise RequestProblem('statistics_observable', str(error)) from error
        result = engine.analyze(initial, f)
        path = engine.sample(initial, f, request.samples, seed=request.trajectory_seed,
            burn_in=request.burn_in, start=request.initialization, class_index=request.stationary_class,
            confidence=request.confidence, max_points=1001)
        return json_arrays({
            'model': 'vertex' if vertex else 'edge', 'orientation': engine.stationary.orientation,
            'start_step': engine.stationary.start_step, 'irreducible': chain.irreducible,
            'atom_labels': list(edge.graph.vertices) if vertex else list(edge.graph.directed_edges),
            'observable': {'kind': request.observable.kind, 'values': f},
            'analysis': result, 'uncertainty': [c.poisson.uncertainty(request.samples, confidence=request.confidence) for c in result.classes],
            'trajectory': path,
            'support': {'source': engine.stationary.support_source, 'policy': chain.support_policy,
                'tolerance': chain.support_atol, 'discarded_entries': chain.discarded_entries,
                'discarded_max_row_mass': chain.discarded_max_row_mass,
                'matrix_change_max_row_l1': chain.matrix_change_max_row_l1},
        })
    except (ValueError, TypeError, KeyError) as error:
        return client_error(error if isinstance(error, RequestProblem) else RequestProblem('statistics_analysis', str(error)))
