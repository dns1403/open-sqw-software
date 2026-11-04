# Validation record — 4 November 2026

Environment: Windows, Python 3.12.14, Node.js 24.22.1. Resolved Python
dependencies are recorded in `requirements-tested.txt`; frontend dependencies
are recorded in `frontend/pnpm-lock.yaml`.

## Phase 4: Poisson equations and trajectory uncertainty

The executed baseline was 301 Python tests, 36 frontend tests and a successful
production build. Phase 4 adds 59 Python cases (23 generic Poisson, 4 classwise,
21 SQW statistics and 11 API) and 8 frontend cases. Full final results:

- `python -m pytest -q`: **360 passed**, **5.08 s**, including all **42 corrected independent
  mathematical handoff checks**. The original oracle and its corrected test copy
  were not edited; no existing assertion/tolerance was weakened.
- `pnpm test`: **44 passed** in six files; last run **4.72 s**.
- `pnpm build`: passed, **87 modules**, **3.61 s**. Existing Plotly chunk warning
  remains (1129.65 kB); no dependency was added for this phase.
- All four original Material SHA-256 hashes match the audit. `git diff --check`
  passes. The pre-existing Starlette/httpx warning remains unsuppressed.

Analytical cases actually computed:

| Case | Computed result |
| --- | --- |
| X-01 / actual DFT path3 atom `(0,1)` | mu=0.25, sigma²=0.125, period 2; instantaneous variance 0.1875 |
| Two-state T with diagonal 2/3 | pi=(0.5,0.5), h=(0.75,-0.75), mu=0.5, sigma²=0.5 |
| Deterministic 4-cycle | period 4, mu=0.25, sigma²=0; a 5-observation prefix still has nonzero error |
| Identity path3, maximally mixed input | two period-2 classes, weights (0.5,0.5), means (0.5,0), both variances 0; no global Gaussian |
| X-04 from delta_2 | transient mass 1, absorption (1,0), limiting law (2/3,1/3,0,0,0), f=1 at vertex 0 gives mu=2/3 and sigma²=2/27=0.074074074… |
| Complex omega/beta and Hermitian observables | direct atom-density traces agree within 3e-14; beta changes f and reuses P/factors |

Regression also covers invalid/nonreal observables and supplied stationary
laws, near-singular weak exits, deterministic periods 1–7, a sparse 200-cycle,
nonreversible/nonuniform chains, shifted/scaled observables, tiny positive
variance, explicit overflow/underflow rejection and 1e-250 reachable class mass. Equal class means with different
variances are not collapsed into a global Gaussian. SQW tests check exact
basis order, outcome/Born distinction, physical starts, burn-in, seed replay,
existing Vertex sampler equivalence, direct densities, cache separation,
artificial stationary starts, downsampling, numerical support suppression and
forbidden density histories. API tests check schema/work limits and cache
invalidation for beta, omega, coins and support.

### Seeded long-trajectory benchmark

Executed `python examples/trajectory_statistics.py` on this Windows workspace,
Python 3.12.14, NumPy 2.5.4, SciPy 1.18.1. Each row uses 256 independent
stationary-start paths with 8192 observations and an atom-0 indicator. Master
seeds are 20261104 (Edge) and 20261105 (Vertex), with SeedSequence child streams.

| Quantity | Edge path3 DFT | Vertex triangle Grover |
| --- | ---: | ---: |
| Period | 2 | 1 |
| Theoretical mu | 0.25 | 0.33333333333333337 |
| Theoretical sigma² | 0.125 | 0.37037037037037035 |
| Exact stationary finite N·Var(mean) | 0.125 | 0.37034625771604934 |
| Observed N·sample variance of means | 0.1424087150424151 | 0.4054117221458234 |
| Grand mean | 0.24986743927001953 | 0.33344316482543945 |
| Observed nominal 95% coverage | 0.93359375 | 0.93359375 |
| Elapsed sampling time | 14.1254 s | 13.6869 s |
| Observations / second | 148467 | 153223 |
| Relative Poisson residual | 0 | 1.67e-16 |

The variance estimates are about 13.9% and 9.5% above theory. Under a Gaussian
approximation, estimating variance from 256 paths has relative standard error
sqrt(2/255), about 8.9%; these differences are unsurprising Monte Carlo scatter.
Observed coverage is evidence, not a finite-sample coverage guarantee. This
benchmark has no stochastic pass/fail threshold. Each path retains two chart
points, counts and a running mean; zero density-history entries are allocated.
These are logical storage counts, not measured process/RSS memory figures.
Timings are local measurements, not cross-hardware performance guarantees.

### Interface verification and commits

Browser checks used actual FastAPI/Vite responses: DFT path3 showed mu=0.25,
sigma²=0.125, SE=0.007906 at N=2000, and a correctly centered shaded envelope.
English/German switching retained all values. Identity path3 displayed two
means (0.5,0), zero variances and no Gaussian band. Selecting/preparing class 2
was explicitly labeled. Vertex coherence ran from t=1. Desktop and 390x844
mobile layouts were inspected; page scroll width equaled client width, legends
and controls were readable, and no browser warning/error logs were recorded.
Unit tests also check stale-response abortion, language/state persistence,
error translation, input validation and band suppression for mismatched classes,
degeneracy, unstable solves and support approximations.

Local tested milestone commits (no remote push):

- `fbfbfe7 feat(statistics): implement finite Markov Poisson solver`
- `a074736 feat(statistics): add classwise asymptotic variance`
- `867f7eb feat(sqw): integrate quantum trajectory uncertainty`
- `cba8f35 feat(ui): add trajectory statistics dashboard`
- `f8ab9c3 fix(statistics): reject unrepresentable observable scales`
- Final documentation/benchmark commit follows this record; use `git log` for
  its hash (a commit cannot include its own hash in its content).

Files: new `core/markov_statistics.py`, `classwise_statistics.py`,
`trajectory_statistics.py`, `api/statistics_cache.py`, their four regression
files, `StatisticsPanel.tsx`, `StatisticsPlot.tsx`, `statisticsTypes.ts`,
`statistics.test.tsx`, EN/DE statistics resources, the benchmark example and
`docs/trajectory_statistics.md`. Existing core exports/reachability, API schema,
stationary cache/routes, UI/i18n/error registration/styles and all requested
project documentation were extended. Original dynamics and research files
are preserved. Optional finite-atomic MMD remains deferred; normal intervals
remain pointwise asymptotic approximations with unquantified transient bias.

## Phase 3: stationary distributions and long-time analysis

The pre-change baseline was executed, not assumed: **242 Python tests**,
**30 frontend tests**, and the TypeScript/Vite production build passed.
Final checks after Phase 3:

- `python -m pytest -q`: **301 passed**, **4.63 seconds**, one existing
  Starlette/httpx deprecation warning. All 42 corrected independent handoff
  checks, including T34, still pass. No existing assertions or tolerances
  were weakened; the independent oracle is unchanged.
- `pnpm test`: **36 passed** in five files, **4.15 seconds**. Six new interface
  tests cover result-driven interpretation, physical time/actual plotted data,
  class-specific density requests, cursor retention, English/German switching
  without requests, localized errors, support validation, horizon invalidation
  and stale-work cancellation. Resource completeness includes `stationary`.
- `pnpm build`: **passed**, 83 modules, **3.35 seconds**. The existing 1,129.65 kB
  Plotly chunk warning remains; no new dependencies were required.
- `git diff --check`: passed. The four original Material files retain their
  SHA-256 hashes from `mathematical_audit.md`; no original research file changed.

New mathematical coverage consists of 21 reusable Markov tests, 25 SQW
stationary tests and 13 API tests. Cases include Identity/Hadamard/Swap path3,
aperiodic triangles, generalized Grover with its two-vertex periodic exception,
DFT structural zeros, exact X-04 port order, complex omega/beta, multiple
closed classes with periods 1/2/3, deterministic cycles through length 7,
coupled transient blocks and fractional absorption. Tiny genuine 1e-24 exit
rates validate the off-diagonal balance and embedded-jump solves. Threshold
tests show that dropping a genuine 1e-16 rate can change the infinite-time
answer. A 500-absorbing-state test checks sparse family/H storage; adapter
tests prohibit calling dense transition builders.

API tests cover original M/P orientation, t=2/t=1 starts, quantum-channel
residuals, exact X-04 class weights, cached structure across initial/horizon/
beta changes, invalidation on coin changes, input/work limits and the sparse
90-state matrix presentation. This does not constitute a load benchmark.

Executed `python examples/stationary_analysis.py` compares reduced means with
independent channel applications through 120 additional transitions. Maximum
matrix-entry discrepancies by example:

| Example | Mean/Kraus error | Stationary channel residual |
| --- | --- | --- |
| Edge path3 Identity | 0 | 0 |
| Edge path3 Hadamard | 4.72e-15 | 5.56e-17 |
| Edge path3 Swap/Grover | 0 | 0 |
| Edge triangle DFT | 3.39e-15 | 8.33e-17 |
| Vertex X-04 | 2.69e-14 | 2.23e-16 |
| Vertex complex omega/beta | 4.11e-16 | 6.21e-17 |

X-04 has closed classes {0,1}, {3,4}, transient state 2, periods 1/1 and
absorption weights (1,0) from delta_2, giving (2/3,1/3,0,0,0). This is the
specified neighbor order, explicitly converted into the repository's ascending
port basis. Small numerical errors are measured evidence, not error bounds
for other models. See [the guide](stationary_analysis.md) for all examples.

Real-browser verification used local FastAPI and Vite:

- Edge path3 Identity: two closed period-two classes, nonunique stationarity,
  correct t=2 start, distinct oscillating ordinary and converging Cesàro curves.
  Class-2 density has trace 1, purity .5 and zero channel residual. Selecting
  class 2 and t=3 survived the English-to-German switch with the same density.
- Exact X-04 was entered through the existing matrix editor, with basis input
  vertex 2. The UI displayed both closed classes, transient 2, weights (1,0)
  and stationary labels (.666667,.333333,0,0,0). Selecting state 2 showed the
  outgoing .5/.5 transitions and the discarded 1.875e-33 artifact separately.
  Stationary density had purity .777778 and channel residual 2.22e-16.
- The actual Cytoscape state graph and Plotly ordinary/Cesàro charts were
  visually inspected. Mobile 390-by-844 checks in both languages reported
  content width=scroll width=375 px, with scrolling tables and no horizontal
  page overflow. The temporary viewport override was reset.
- Browser console: no warnings or errors during these checks. Saved evidence:
  [X-04 graph and weights](screenshots/stationary-x04-en.png) and
  [German periodic/Cesàro curves](screenshots/stationary-de.png).

Files added: `core/markov_analysis.py`, `core/structural_support.py`,
`core/stationary.py`, `api/stationary_cache.py` under `backend/sqw/`;
`tests/test_markov_analysis.py`, `tests/test_stationary.py`,
`tests/test_stationary_api.py`; `examples/stationary_analysis.py`;
`frontend/src/{StationaryPanel,StationaryPlot,ReducedMarkovGraph}.tsx`,
`frontend/src/__tests__/stationary.test.tsx`, both `stationary.json` locales;
`docs/stationary_analysis.md` and the two screenshots above.
Modified: core exports and Edge/Vertex support accessors; API schemas/routes;
App integration, shared density table export, types, API error mapping, i18n
registration/error resources and styles; README, AGENTS, architecture, theory,
mathematical-results mapping, roadmap and this validation record.

No full quantum superoperator, spectral-gap bound, infinite-graph extension
or approximate duplicate-projector merge was introduced. Numerical support
uncertainty, sparse-solve fill-in and the existing dense Vertex constructor
remain limitations. The runtime cache is bounded and is not experiment storage.

## Exact Markov engines and mathematical integration

Final checks after this implementation pass:

- `python -m pytest -q`: **242 passed**, one existing Starlette/httpx warning,
  **4.40 seconds**. This includes all 42 independent corrected handoff checks,
  existing baseline tests and new core/ensemble/API regressions.
- `pnpm test`: **30 passed** in four files, **4.60 seconds**. The eight added
  interface tests cover vertex mode/strategy, complex parameter drafts, localized
  errors, stale-request cancellation, result retention across languages and
  one-step playback/pause without future requests. They also ensure that changing
  ensemble size clears old statistics and returning to vertex mode restores
  the applied omega/beta values in the editor. Translation completeness
  checks now also cover the `research` namespace.
- `pnpm build`: **passed** TypeScript and Vite, 78 modules, **3.37 seconds**.
  Two unsupported Testing Library option types in the new test file were fixed
  during final build verification; no production behavior was changed for that.
- `git diff --check`: passed. Windows LF/CRLF notices are not whitespace errors.
- The four original Material hashes and the PDF hash match the audit record.
  An AST comparison confirms all **42 original test bodies are unchanged** in
  the corrected independent copy. The original suite still reproduces its
  documented T34 failure; its tolerance was not increased.

Deterministic reference comparisons cover path-3, triangle and star graphs;
identity, Hadamard, Grover, DFT and random unitary coins; complex pure and
coherent mixed inputs; zero transitions, reducible/periodic cases; complex omega
and nonzero beta. Full positive short Kraus words check joint probabilities,
conditional densities and pre-scattering reductions. Reduced means are compared
with independent Kraus evolution, including observables, positivity, trace,
purity, q2, orientation and time indexing. Seeded tests check reproducibility;
different sampling strategies are compared by their laws, not identical draws.

Monte Carlo tests use 3000 independent paths and a conservative 0.065 marginal
error bound, separately from deterministic equality tolerances. A 20000-path
test checks compact selected histories and label-to-Born timing. Source AUD-01
through AUD-05 restrictions have regression coverage. Tests of local evolution
also forbid accidentally constructing dense global M/U matrices.

[Actual benchmarks](benchmarks.md) compare both samplers on four small models
and run 50000 optimized paths for 40 steps on a 32-vertex cycle. In those five
benchmark configurations, the maximum matrix-entry discrepancy between exact
reduced means and independent Kraus means through t=8 was **8.33e-16**. This is
not a universal error bound. Runtime and separately traced peak allocations
are recorded in `benchmarks.json`; they do not include API/UI overhead.

Real-browser checks against FastAPI and Vite:

- Edge triangle, DFT, maximally mixed input: conditional purity **0.5000 at
  t=1**, **1.0000 at t=2**, with explicit atom `(0,2)` and coherent scattered
  ket reconstruction. The inspector reports column M, and the ensemble reports
  separate preparation-label and vertex Born TV deviations.
- A 1000-path, six-step edge ensemble had final Born TV **0.019333** and label
  TV **0.039000**. Switching to German kept trajectory t=2, the ensemble and
  inspector values, while displayed probabilities adopted decimal commas.
- Separate vertex model with omega `[0.6, 0.8i]` at every triangle vertex and
  beta `{0:0.3, 1:-0.7, 2:1.1}`: conditional purity one after the first step;
  reconstructed complex chi; row P; disabled edge-observable tab. Reference
  and optimized six-step means both displayed purity **0.5264**.
- Play advanced requested prefixes, pause stopped at t=6 and the cursor stayed
  there during later ensemble, inspector and language interactions. JSON
  parameter drafts and computed results survived language switching.
- At 390×844, the document width was 375 px with no horizontal page overflow.
  Wide numerical tables scroll within their panels; the heatmap remains usable.
  The temporary viewport override was reset. Browser console: **no errors or
  warnings** during these checks.
- Saved evidence: [English vertex experiment](screenshots/markov-vertex-en.png),
  [German vertex experiment](screenshots/markov-vertex-de.png), and
  [German inspector view](screenshots/markov-inspector-de.png).

Reproduce tests/build with the README commands. Run
`python examples/benchmark_markov.py` for fresh measurements and
`python tests/test_reference_handoff.py` for the standalone corrected oracle.
`python Material/reference_checks.py` intentionally retains the original 41/42
result. See the [audit and changed-file inventory](mathematical_audit.md),
[result-ID mapping](mathematical_results.md), and [remaining scope](roadmap.md).

## Historical English/German internationalization pass

Executed after the bilingual implementation:

- `python -m pytest -q`: **104 passed**, one upstream deprecation warning,
  in 1.68 seconds. The original 97 mathematical/API tests remain passing;
  seven additional API tests cover structured errors and language-independent
  numerical behavior. No files in `backend/sqw/core` were changed for i18n.
- Final `pnpm test`: **22 passed** in three files, in 4.21 seconds. Tests cover the
  English default regardless of browser language, explicit persisted choices,
  unavailable storage, document language, English fallback, matching resource
  keys/interpolation parameters, and resolution of every translation key.
- Interface tests exercise all three available simulation modes in both
  languages; graph/matrix/seed/initial-state/cursor retention; draft retention;
  unchanged simulation request payloads; in-flight requests; live translation
  of existing API and matrix-validation errors; keyboard switching; and
  localized Plotly labels, hover values and built-in interaction tips with
  unchanged numeric data. Canvas
  libraries are mocked in these component tests and exercised separately in
  the real browser.
- Final `pnpm build`: **passed**, including TypeScript and Vite. Vite transformed
  75 modules and completed bundling in 3.28 seconds. The existing Plotly bundle
  size warning remains; see below.

Real browser checks against running FastAPI and Vite servers:

- A fresh page starts in English. The EN | DE header control changes labels,
  help, chart text, error banners, accessibility labels, metadata and the
  document language without a page refresh.
- On a three-vertex cycle in open mode, changing to German retained the graph,
  selected vertex, six-step history and cursor at step five, and the edited
  matrix draft. A visible nonunitary-matrix error changed language immediately.
  Purity changed presentation from `0.1736` to `0,1736`.
- Explicit German and English choices each survived a reload. Reloading starts
  a fresh experiment, as before; only the language preference is persisted.
- A 12-step quantum trajectory on a six-vertex cycle retained its step and
  measurement record across language switches. Both language versions were
  visually inspected and saved as [English](screenshots/lab-en.jpg) and
  [German](screenshots/lab-de.jpg) screenshots.
- At a 390 × 844 viewport, both languages remained usable with the switcher
  visible and no horizontal page overflow (content width 375 pixels). The
  temporary viewport override was reset after checking.
- The browser console contained no errors or warnings during the bilingual
  verification.

## Files changed or added for i18n

- Configuration and documentation: `.gitignore`, `AGENTS.md`, `README.md`,
  `docs/architecture.md`, `docs/theory.md`, `docs/roadmap.md`,
  `docs/mathematical_results.md`, this validation record, and
  `docs/screenshots/lab-en.jpg`, `docs/screenshots/lab-de.jpg`.
- Frontend setup: `frontend/package.json`, `frontend/pnpm-lock.yaml`,
  `frontend/index.html`, `frontend/vitest.config.ts`, `frontend/src/main.tsx`.
- Interface: `frontend/src/App.tsx`, `frontend/src/LanguageSwitcher.tsx`,
  `frontend/src/GraphView.tsx`, `frontend/src/MatrixEditor.tsx`,
  `frontend/src/ProbabilityPlot.tsx`, `frontend/src/styles.css`,
  `frontend/src/api.ts`.
- Localization: `frontend/src/i18n/index.ts`, `frontend/src/i18n/format.ts`,
  `frontend/src/i18n/locales/en/{app,components,errors}.json` and the matching
  files under `de/`.
- Frontend tests: `frontend/src/__tests__/setup.ts`, `i18n.test.ts`,
  `api.test.ts`, and `interface.test.tsx`.
- API error adapter and regressions: `backend/sqw/api/app.py`,
  `backend/sqw/api/errors.py`, `tests/test_api.py`.

## Initial implementation checks

Before the i18n follow-up, the initial implementation passed 97 Python tests
and `pnpm install --frozen-lockfile` / `pnpm build`. Additional executed checks:

- `python examples/edge_walk.py` succeeded. The triangle with DFT scattering
  and uniform initial state had open-state purity approximately 0.168403 after
  six steps, with distinct unitary and open distributions.
- FastAPI health checks succeeded directly and through the Vite proxy.
- Browser checks covered a three-vertex path with Grover matrices, directed
  initial states, run/back/step controls, and vertex selection by graph click
  and dropdown.
- The matrix editor rejected `2I`, accepted `diag(1, i)`, and used the valid
  complex matrix in the next simulation step.
- The open triangle displayed purity 0.1684 after six steps, matching the
  Python example. Trajectory measurement records used the documented
  post-scattering state indexing.
- An initially observed Plotly resize error was fixed and did not recur in
  the repeat browser check. Mobile checks found no horizontal page overflow.

## Known warnings and historical scope

Starlette's TestClient emits an upstream warning about replacing its `httpx`
adapter with `httpx2`. The current adapter works; the warning is not suppressed.
Vite warns about the separately bundled Plotly chunk exceeding 500 kB
(1,129.65 kB minified). The build succeeds. After installation, the application
does not require external fonts or cloud resources.

All currently implemented application text has English and German resources.
Scientific names, mathematical expressions, matrix entries, JSON, and stable
model/graph identifiers intentionally retain their canonical form. The API's
original English `detail` remains for machine-client compatibility; the UI uses
localized stable error codes and a localized generic fallback for unknown
errors. The API documentation and technical project documentation are English.

At the end of the earlier i18n pass, the induced vertex channel was Python-only
and its UI control was disabled. That historical limitation and missing playback
are superseded by the exact-Markov pass above. Full experiment persistence
remains planned.

The development sandbox initially blocked local socket pairs and loopback
connections. Python tests and preview servers ran with approved local network
access. Normal terminal commands in the README remain valid. No public
deployment, long-duration test, or load test was performed. Tests establish
the listed reference cases and invariants, not proofs for future optimizations.
