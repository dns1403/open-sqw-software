# Architecture

`sqw.core` contains mathematics and NumPy/SciPy/NetworkX only. `sqw.api`
translates validated JSON experiments into core calls. `frontend/` renders
responses and maintains interface state. There is no database or server-side
simulation session. Notebook use requires neither FastAPI nor React.

```text
React + TypeScript + Cytoscape + Plotly + i18next
                | /api, Vite proxy
FastAPI + Pydantic: Experiment -> Frames
                |
GraphModel + ScatteringWalk + ReferenceTrajectory
                |
NumPy + SciPy CSR + NetworkX
```

## Responsibilities

- `core/graph.py`: validated simple connected graphs and immutable basis/neighbor
  orderings. Integer vertex labels are sorted.
- `core/scattering.py`: local matrix presets and unitarity validation.
- `core/states.py`: state constructors and explicit numerical validation.
- `core/walk.py`: sparse `U`, pure evolution and the direct open channel.
  Computing `S(x) rho[I_x,I_x] S(x)†` is an exact evaluation of the Kraus sum;
  it assumes neither diagonal states nor a Markov reduction.
- `core/trajectories.py`: general measurement/reduction/scattering reference
  algorithm for both state vectors and mixed density matrices.
- `core/vertex.py`: independent induced vertex channel with configurable
  `omega`, `beta`, boundary operator and a separately exposed Markov matrix.
- `core/edge_markov.py`: E-02--E-05 eligibility, exact warmstart, local M,
  compact online paths and reduced means with lazy reconstruction.
- `core/vertex_markov.py`: V-01/V-02/V-04/V-06 sparse chi/P, compact vertex
  paths and means, and beta updates that reuse P.
- `core/ensembles.py`: grouped vectorized ID sampling or streamed independent
  reference paths; requested counts/Born statistics and selected histories.
- `core/markov_analysis.py`: reusable row-stochastic CSR validation, support,
  SCCs, periods, stationary families, absorption solves and Cesàro evolution.
- `core/structural_support.py`: conservative exact recognition of built-in
  support formulas; metadata never edits a quantum operator or state.
- `core/stationary.py`: explicit M-transpose/P adapters, q2/r0 initialization,
  invariant label measures and lazy phase-sensitive stationary barycenters.
- `core/markov_statistics.py`: centered sparse bordered Poisson LU, stable
  martingale variance, independent identity checks and uncertainty diagnostics.
- `core/classwise_statistics.py`: one reusable factorization per existing closed
  class, absorption-weighted random limits and conservative global-CLT fields.
- `core/trajectory_statistics.py`: Hermitian atom expectations, recorded outcome
  and next-Born semantics; original-transition sampling without density history.
- `api/statistics_cache.py`: bounded structural (16) and phase-specific (32)
  engines. Graph/coin/omega/support changes invalidate factors; beta changes
  invalidate quantum observables while sharing factors. Each solver and engine
  retains at most 16 observable entries; shared mutation/solves are locked.
- `api/stationary_cache.py`: bounded 16-model structural cache keyed by complete
  graph, complex coin/omega bytes and support policy; independent of initial
  state, horizon, seed once coins are fixed, and beta. Beta updates retain the
  same P/class analysis while rebuilding chi.
- `api/schemas.py`: versionable JSON contract; complex values are `[real, imag]`.
- `api/app.py`: deterministic experiments, diagnostics and API boundary checks.
- `api/errors.py`: stable error descriptors for presentation, preserving the
  existing English diagnostics. It does not modify mathematical validation.
- `frontend/src/i18n/`: bundled English/German resources, explicit language
  preference, English fallback, metadata and observable number formatting.
- `frontend/src/ResearchPanels.tsx`: ensemble comparison/heatmap, atom/matrix
  inspector and complex omega/beta controls. No physics is computed in the UI.
- `frontend/src/StationaryPanel.tsx`, `ReducedMarkovGraph.tsx`, `StationaryPlot.tsx`:
  dedicated bilingual stationary analysis, sparse transitions, class colors,
  stationary weights, physical-time ordinary/Cesàro charts and quantum density.
- `frontend/src/StatisticsPanel.tsx`, `StatisticsPlot.tsx`, `statisticsTypes.ts`:
  observable and trajectory controls, class statistics, running mean and
  asymptotic envelope, translated diagnostics and independent-sampling comparison.

## Memory and extension points

Pure states require O(|D|) storage; `U` is a CSR matrix. The dense reference
state requires O(|D|²), but no |D|² × |D|² superoperator is constructed.
Dense projectors and Kraus operators are diagnostic objects allocated only
when explicitly requested. Trajectories retain vectors for pure initial states.

`PureStateStepper`, `DensityStepper` and `TrajectoryEngine` describe the original
full-state reference interfaces. Compact results deliberately have a separate
contract: `start(initial).step()` returns a stage-specific state with `density()`,
`ket()`, `reduced_density()` and Born queries that allocate only on demand.
`run` retains the initial state, edge first local state and later IDs; online
sessions retain only the current state. `iter_mean` yields local first blocks
and then label weights. Kets agree up to global phase; densities are directly
comparable. Reference methods never call the optimized engines.

After warmstart, edge paths require O(1) state metadata and local coin storage;
mean weights require O(D), with an O(sum_x degree(x)^2) M multiplication.
Vertex chi/P storage is sparse O(|V|+|D|). Its existing InducedVertexWalk
constructor still constructs dense diagnostics before reduction: very large
vertex models need a future sparse constructor. Requested dense reconstruction
costs O(d²). The input mixed density itself also costs O(d²).

Optimized ensembles keep O(N) current IDs, O(T*d) requested statistics and
O(k*T) selected histories, not N*T density matrices. The reference processes
one full path at a time; its peak includes that path's T full states. Exact
comparison statistics use the reduced mean engine for either sampler; tests
separately compare those exact curves against full Kraus sums. Independent
samplers are compared statistically, not by equality of differently consumed RNGs.

Record new theorems, hypotheses and proof status in `mathematical_results.md`
before implementing a separately selectable strategy with reference comparisons.
There is no implicit switch to an assumed Markov dynamics.

## Independent induced vertex walk

The Section-6 model has its own Hilbert space C^|V|, initial states and Kraus
operators. Its adapter must never label an edge-walk marginal as a vertex walk.
The Python core implements normalized local `omega(x)`, the boundary operator
`R`, `theta(x)`, phases `beta_x` and completed vectors `chi(x)`; see `theory.md`.
The separate enabled `vertex` mode selects conditional trajectories or mean
dynamics. Edge probabilities are absent in that model. Its displayed dimension
is |V| and its localized initial state is a vertex, not a directed edge.

## API and interaction

- `GET /api/health`: readiness and version.
- `POST /api/graph`: graph preset, size, scattering preset and seed -> basis/matrices.
- `POST /api/scattering`: local matrix for a degree and seed.
- `POST /api/simulate`: complete configuration -> frames from t=0 through t=n.
- `POST /api/ensemble`: configuration + trajectory count, requested statistics
  and selected-history count -> aggregate frames and compact records.
- `POST /api/analysis`: configuration + `atom_id` -> small-system transition,
  quantum-state and pre-scattering conditional-state diagnostics.
- `POST /api/stationary`: open/trajectory/vertex configuration + `analysis_steps`
  (0..5000, default 200), `support_atol` (0..1e-6, default 1e-14), optional
  `include_density` and zero-based `stationary_class` in closed-class order.
  Returns class IDs/membership/periods/cyclic subclasses, stationary-family rows,
  absorption H, input law, class weights, mixture, support diagnostics, original
  sparse probabilities, raw finite-time curves and optional quantum density.
  Full matrices and dense quantum inspection are limited to dimension 64;
  histories require dimension*(analysis_steps+1) <= 250000. `analysis_steps`
  counts transitions after t=2 (Edge) or t=1 (Vertex), independently of `steps`.
- `GET /docs`: generated OpenAPI documentation.

The API accepts `initial.kind` equal to `basis`, `uniform`, `pure`, `mixed` or
`maximally_mixed`; custom `vector` and `density` use complex pairs. Vertex basis
states use `initial.vertex`, edge basis states use `initial.edge`. Validity
checks are identical to Python input checks. The browser offers basis, uniform
and maximally mixed preparations. Vertex parameters are dictionaries
`omega: {vertex: complex_vector}` and `beta: {vertex: real_phase}`.
`size` always denotes the total number of vertices, including the center of a
star. Matrix overrides must cover exactly all vertices.

Interactive requests are limited to 32 vertices, 256 directed edges and 200
steps, with a dense reference/mixed unitary limit d²(n+1) <= 12 million. These
UI limits are not mathematical constraints on the core. `open` evolves means,
`unitary` evolves pure or mixed states, `trajectory` samples an edge path and
`vertex` uses its own model with `vertex_dynamics=trajectory|mean`.
`strategy=reference|optimized` is explicit (API default reference; UI default
optimized). Unitary evolution always reports reference; it has no atom reduction.
Frame n includes X_n and the measurement distribution evaluated before that
step, on the state at n-1.

Frames add `stage`, `state_kind`, `atom_id`, `atom_edge`/`atom_vertex` and mean
`state_weights` when applicable. Atom IDs follow the graph basis. Conditional
densities are not included in each frame; the inspector reconstructs only its
requested state. At warmstart there is no fictitious fixed-atom label.

Ensembles accept N <= 100000, N*max(1,T) <= 10 million and at most 20 selected
histories (also <= N). Reference ensembles additionally require N*max(1,T)*d²
<= 50 million. `statistics` selects `states`, `vertices`, `edges`, `exact`.
`state_counts` and `outcome_counts` are integer counts; `empirical_born_*` average
quantum states without an extra measurement. Label TV is undefined before the
fixed-atom stage. Vertex edge-statistics fields are absent/null.

Dense analysis is limited to dimension 64 and reports `orientation=column|row`,
atom labels, selected ket, full transition matrix, next-label probabilities and
eligibility assumptions. These are explicit allocations, not part of efficient
stepping. Unsupported graph/instrument extensions are rejected with a reason.

Requests are stateless. A longer request with the same seed reproduces the same
trajectory prefix for step controls. Changing an experiment configuration clears
its previous results. Changing the presentation language does not change the
configuration, invoke the API, remount the graph or discard results. Vite proxies
API requests through the same browser origin.
Play schedules one additional requested step at a time (600 ms pacing); pause
cancels the next scheduled request. It never requests a future path in advance.
A stateless request replays its prefix; Python sessions avoid that O(T) replay.
Inspector queries replay the requested prefix without advancing the displayed
experiment. Mathematical input changes abort stale ensemble/inspector work.
The stationary panel likewise aborts stale requests and clears results when
the experiment or its analysis controls change. Class/state selection and
language changes operate on retained responses; density reconstruction is an
explicit request. Backend structural caching is separate from this UI state.
See [stationary analysis](stationary_analysis.md) for support-policy semantics
and sparse solve costs; the original raw matrix remains available for curves.

## Internationalization boundary

English is the initial and fallback language. Only explicit choices from the
header switcher are persisted under `sqw.language`; browser language detection
is intentionally absent. Resources are bundled under `i18n/locales/{en,de}/`
in the `app`, `components`, `research`, `stationary`, `statistics` and `errors` namespaces. Resource initialization is
synchronous. Language changes update the document `lang` and metadata and
rerender presentation without changing component identities.

Translated chart labels and preformatted hover text are derived from the same
numeric arrays. Matrix JSON, numerical inputs, random streams, equations,
vertex labels and serialized model identifiers remain unchanged. Existing
matrix drafts and error descriptors remain in state when switching languages.

API error responses preserve `detail` and add `code` and `params`. Request
validation also supplies safe `issues` with a stable code, field path and
numeric constraints, excluding rejected nonfinite input. The frontend maps
these codes through the `errors` namespace at render time. Unknown codes use
a localized generic fallback; the original English detail remains available to
machine/API consumers without being injected into the localized interface.

## Statistics API contract

`POST /api/statistics` takes an open/trajectory/vertex `SimulationRequest` plus:

- `observable`: `kind` (`label_indicator`, `outcome_indicator`,
  `vertex_probability`, `coherence_real`, `coherence_imag`, `quantum`,
  `label_values`), zero-based `index`/`second`, actual `vertex` label,
  optional complex-pair Hermitian `matrix`, optional real `values`.
- `samples`: 1..100000 observations (default 2000), `burn_in`: 0..10000
  discarded observations, `trajectory_seed`: uint32 (default 42),
  `confidence`: strictly between 0 and 1 (default .95).
- `initialization`: `experiment` or explicitly prepared `stationary_class`;
  `stationary_class`: zero-based closed-class index (default 0).
- `support_atol`: 0..1e-6, default 1e-14. Analytical support takes precedence.

The inherited `steps` does not set N. Inherited `seed` controls random coins;
`trajectory_seed` controls the new sampled path. Dense Hermitian inspection
is limited to dimension 64 and total dimension*(N+burn_in) to 5000000.
Errors use the existing localized descriptor mechanism. Responses include
original orientation, atom start time/labels, observable values, classwise
Poisson solutions, absorption weights, residuals, stability diagnostics,
conditional uncertainties, and an empirical law/mean with at most 1001 points.
Returned points retain physical step and observation count; all observations
contribute even when chart points are thinned. No density history is returned.

Class weights and global-CLT fields describe the original experimental input.
Artificial stationary initialization is marked separately with its selected
class. The browser class selector inspects retained data and specifies the
class for the next explicit stationary-start run; it never silently resamples.
Sampling-control changes clear displayed results; experiment changes abort
stale responses. Language changes preserve all state and make no request.
Aborting a browser request does not yet cancel server-side computation.

Sparse LU can have fill-in. Small-class condition estimates cost dense cubic
work (dimension <=128); larger classes omit that estimate. Sampling retains
O(d + displayed points) state after constructing transition tables. The existing
Vertex constructor still has its documented dense diagnostic allocations.

## Custom graph editor and experiment files

`customGraph.ts` owns the pure draft operations, deterministic graph projection,
port-bound matrix records, omega bindings, physical-basis-bound initial states,
and versioned document conversion. `matrixValidation.ts` provides a restricted
complex grammar (no expression evaluation), dimension checks and the same
max-entry unitarity residual/tolerance as the core. The server remains the
final validator for physical inputs.

`GraphView.tsx` extends the existing Cytoscape canvas with optional edit callbacks
and stored positions. `CustomGraphTools.tsx` supplies explicit modes, list-based
connections, deletion and rename controls. `MatrixEditor.tsx` adds per-cell
complex input and residuals to its existing JSON editor. `InitialStateInput.tsx`
exposes pure/mixed input with ordered labels. `ExperimentFiles.tsx` validates
before import/replacement or download; `ConfirmationDialog.tsx` uses an accessible
app-owned modal, avoiding native dialogs that block embedded browser control.
All new strings live in `components.editor`, existing app keys and errors.

`App.tsx` keeps custom and preset data independent. It binds each accepted matrix
to its exact physical ports; unapplied text is separately retained. Editing
layout/labels does not change experiment payloads. Scientific edits clear
histories and invalidate serialized experiment keys consumed by research panels.
Pending validation/import locks editor operations. Physical basis states bind
to actual vertex/arc labels; arbitrary vectors/densities bind to the complete
ordered basis and require explicit review when it changes.

`GraphSpec(kind='custom')` passes through the same `build_walk` and all existing
engines. Neighbor lists are checked against canonical sorted IDs. The versioned
`ExperimentDocument` adds presentation metadata around `SimulationRequest`;
`POST /api/experiments/validate` validates both physical and presentation data,
including inactive saved omega/beta. Absent server parameters (`null`) are
converted to automatic defaults in the draft rather than manual zero vectors.
`POST /api/scattering/validate` validates one local matrix while other vertices
are unfinished. Neither endpoint adds an alternate simulator or relaxes
stationary/Poisson eligibility, support policy, memory budgets or time indexing.

See [custom graphs](custom_graphs.md) for schema, migration policy and persistence
scope. JSON v1 intentionally rejects noncanonical port permutations. Session
state and secondary analysis controls are not a new server-side storage model.
