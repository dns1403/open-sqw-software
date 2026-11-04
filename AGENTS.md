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

## Development
- Work in this checkout; preserve user-provided research and files.
- Python package metadata is at the repository root. Use `python -m pytest` for mathematical/API tests and `npm run build` in `frontend` for TypeScript/build verification.
- Keep dependency lockfiles for the frontend. Do not commit environments, generated builds, caches, or temporary paper extractions.
- Add meaningful mathematical regression tests when changing the core. Update theory/architecture docs when semantics change.
- New mathematical results belong in `docs/mathematical_results.md`, with hypotheses, provenance, proof status, and validation requirements.
- Keep the application local by default. No database, authentication, or cloud dependency is needed.

## Internationalization
- English is the default and fallback. Only an explicit stored language choice overrides it; do not infer the language from browser settings.
- Put user-facing text in the matching `app`, `components`, or `errors` namespaces under `frontend/src/i18n/locales`. Keep keys and interpolation parameters consistent across languages.
- Language changes must preserve experiment state and must not trigger graph or simulation requests. Translate error descriptors when rendering, not when catching errors.
- Preserve mathematical notation, matrix JSON, model identifiers, and API fields. Format observable numbers only for display. Run `pnpm test` and `pnpm build` in `frontend` after UI changes.
