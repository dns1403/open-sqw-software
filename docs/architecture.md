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
- `api/schemas.py`: versionable JSON contract; complex values are `[real, imag]`.
- `api/app.py`: deterministic experiments, diagnostics and API boundary checks.
- `api/errors.py`: stable error descriptors for presentation, preserving the
  existing English diagnostics. It does not modify mathematical validation.
- `frontend/src/i18n/`: bundled English/German resources, explicit language
  preference, English fallback, metadata and observable number formatting.

## Memory and extension points

Pure states require O(|D|) storage; `U` is a CSR matrix. The dense reference
state requires O(|D|²), but no |D|² × |D|² superoperator is constructed.
Dense projectors and Kraus operators are diagnostic objects allocated only
when explicitly requested. Trajectories retain vectors for pure initial states.

`PureStateStepper`, `DensityStepper` and `TrajectoryEngine` define extension
points for alternative strategies. New strategies must use the same basis
ordering, time indexing and observable semantics, and must be tested against
the reference. A future ensemble engine can accumulate results incrementally
without retaining every path. Spectral methods can use `apply_channel` as a
linear operation.

Record new theorems, hypotheses and proof status in `mathematical_results.md`
before implementing a separately selectable strategy with reference comparisons.
There is no implicit switch to an assumed Markov dynamics.

## Independent induced vertex walk

The Section-6 model has its own Hilbert space C^|V|, initial states and Kraus
operators. Its adapter must never label an edge-walk marginal as a vertex walk.
The Python core implements normalized local `omega(x)`, the boundary operator
`R`, `theta(x)`, phases `beta_x` and completed vectors `chi(x)`; see `theory.md`.
The interface reserves a disabled mode until a separate experiment contract
and full controls are available.

## API and interaction

- `GET /api/health`: readiness and version.
- `POST /api/graph`: graph preset, size, scattering preset and seed -> basis/matrices.
- `POST /api/scattering`: local matrix for a degree and seed.
- `POST /api/simulate`: complete configuration -> frames from t=0 through t=n.
- `GET /docs`: generated OpenAPI documentation.

The API currently accepts pure basis/uniform initial states. The Python core
also supports arbitrary validated complex vectors and density matrices.
`size` always denotes the total number of vertices, including the center of a
star. Matrix overrides must cover exactly all vertices.

Interactive requests are limited to 32 vertices, 256 directed edges and 200
steps, with an additional open-run limit |D|²(n+1) <= 12 million. These UI limits
are not mathematical constraints on the core. `open` evolves density matrices,
`unitary` evolves vectors, and `trajectory` generates one conditional realization.
Frame n includes X_n and the measurement distribution evaluated before that
step, on the state at n-1.

Requests are stateless. A longer request with the same seed reproduces the same
trajectory prefix for step controls. Changing an experiment configuration clears
its previous results. Changing the presentation language does not change the
configuration, invoke the API, remount the graph or discard results. Vite proxies
API requests through the same browser origin.

## Internationalization boundary

English is the initial and fallback language. Only explicit choices from the
header switcher are persisted under `sqw.language`; browser language detection
is intentionally absent. Resources are bundled under `i18n/locales/{en,de}/`
in the `app`, `components` and `errors` namespaces. Resource initialization is
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
