# Scattering Quantum Walk Lab

## Scientific contract
- Preserve Joye arXiv:2409.08428v2 conventions: `(x, y)` / `|xy>` means the directed edge **from y to x**.
- Read `docs/theory.md` and relevant sections of the reference PDF before changing mathematical operators.
- Keep vertex order, neighbor order, and directed-edge basis explicit and deterministic. Matrix rows index outgoing neighbors, columns incoming neighbors.
- Keep numerical core in `backend/sqw/core`, independent of FastAPI and frontend.
- Validate dimensions, finiteness, normalization, Hermiticity, positivity, and unitarity with explicit tolerances. Never silently repair invalid user input.
- Implement optimizations only with stated assumptions and tests against the direct reference algorithm. No unproved reductions.
- Induced vertex channels are distinct from edge-walk vertex marginals.
- Record trajectory time indices and RNG semantics; use explicit NumPy generators, never global random state.
- Edge atom weights use column-stochastic `q_next = M @ q`; vertex preparation labels use row-stochastic `q_next = q @ P`. Keep these orientations explicit.
- Preserve full incoming coherence blocks in edge `q2`. Conditional edge atoms start at t=2, vertex atoms at t=1. Atom weights, Born laws, mean densities and observed-outcome counts are distinct outputs.
- Keep the four original files in `Material/` unchanged. See `docs/mathematical_audit.md` for the transparent T34 numerical correction and the independent test copy. Numerical checks are not proofs.
- Reject unsupported instruments/partial observation/time-dependent coins from exact reductions. Do not extend simple-graph purification to parallel ports without a new contract.
- Stationary structure uses a row-stochastic generic engine: explicitly adapt edge M by transpose, preserve original display orientation and atom start times. Closed classes and cycle-length gcd periods come from transition support, never the original undirected graph alone.
- Prefer declared analytical support for exactly recognized formulas; otherwise report the probability cutoff, removed mass and changed analysis matrix. Tiny genuine rates can change infinite-time limits. Keep original operators and finite-time curves intact; residuals do not certify asymptotic accuracy.
- Solve a stationary law per closed class and include transient absorption via a_j = q_start @ h_j (AUD-01/X-04). Uniqueness, irreducibility and ordinary convergence are separate properties. A periodic class removes an arbitrary-input convergence guarantee, not convergence for every individual input.
- Keep stationary label measures, their quantum barycenters, ensemble Cesàro averages and single-path empirical averages distinct. Preserve complex omega/beta in atom reconstruction. Cache graph/coins/omega/support separately from initial inputs and beta.

## Development
- Work in this checkout; preserve user-provided research and files.
- Python package metadata is at the repository root. Use `python -m pytest` for mathematical/API tests and `npm run build` in `frontend` for TypeScript/build verification.
- Keep dependency lockfiles for the frontend. Do not commit environments, generated builds, caches, or temporary paper extractions.
- Add meaningful mathematical regression tests when changing the core. Update theory/architecture docs when semantics change.
- New mathematical results belong in `docs/mathematical_results.md`, with hypotheses, provenance, proof status, and validation requirements.
- Keep the application local by default. No database, authentication, or cloud dependency is needed.
- Inspect branch, status, history and Git configuration at the start of each implementation phase. Preserve unrelated changes and existing history; follow the existing branch workflow.
- Commit each logically complete milestone locally after inspecting its diff and running relevant tests. Stage only task-related files; exclude environments, caches, temporary files and large generated benchmark artifacts. Report commit hashes and messages.
- Never force-push, hard-reset or rewrite history. Do not push to any remote without explicit user authorization. If pre-existing changes obstruct an atomic commit, preserve them and explain the conflict.

## Internationalization
- English is the default and fallback. Only an explicit stored language choice overrides it; do not infer the language from browser settings.
- Put user-facing text in the matching `app`, `components`, `research`, `stationary`, or `errors` namespaces under `frontend/src/i18n/locales`. Keep keys and interpolation parameters consistent across languages.
- Language changes must preserve experiment state and must not trigger graph or simulation requests. Translate error descriptors when rendering, not when catching errors.
- Preserve mathematical notation, matrix JSON, model identifiers, and API fields. Format observable numbers only for display. Run `pnpm test` and `pnpm build` in `frontend` after UI changes.
