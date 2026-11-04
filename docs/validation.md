# Validation record — 4 November 2026

Environment: Windows, Python 3.12.14, Node.js 24.22.1. Resolved Python
dependencies are recorded in `requirements-tested.txt`; frontend dependencies
are recorded in `frontend/pnpm-lock.yaml`.

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
