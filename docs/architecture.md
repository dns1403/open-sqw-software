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
- `api/schemas.py`: versionable JSON contract; complex values are `[real, imag]`.
- `api/app.py`: deterministic experiments, diagnostics and API boundary checks.
- `api/errors.py`: stable error descriptors for presentation, preserving the
  existing English diagnostics. It does not modify mathematical validation.
- `frontend/src/i18n/`: bundled English/German resources, explicit language
  preference, English fallback, metadata and observable number formatting.
- `frontend/src/ResearchPanels.tsx`: ensemble comparison/heatmap, atom/matrix
  inspector and complex omega/beta controls. No physics is computed in the UI.

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

## Internationalization boundary

English is the initial and fallback language. Only explicit choices from the
header switcher are persisted under `sqw.language`; browser language detection
is intentionally absent. Resources are bundled under `i18n/locales/{en,de}/`
in the `app`, `components`, `research` and `errors` namespaces. Resource initialization is
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
