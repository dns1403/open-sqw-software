# Validation record — 4 November 2026

Environment: Windows, Python 3.12.14, Node.js 24.22.1. Resolved Python
dependencies are recorded in `requirements-tested.txt`; frontend dependencies
are recorded in `frontend/pnpm-lock.yaml`.

## English/German internationalization

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

## Known warnings and scope

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

The induced vertex channel remains Python-only; its UI control is disabled
with a translated explanation. Other previously planned features remain
planned. This task does not add playback, full experiment persistence, or
additional simulation modes.

The development sandbox initially blocked local socket pairs and loopback
connections. Python tests and preview servers ran with approved local network
access. Normal terminal commands in the README remain valid. No public
deployment, long-duration test, or load test was performed. Tests establish
the listed reference cases and invariants, not proofs for future optimizations.
