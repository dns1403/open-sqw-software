# Mathematical handoff audit — 4 November 2026

The four handoff files and the existing core/API/UI/tests were inspected before
the reductions were introduced. The baseline passed 104 Python and 22 frontend
tests. The original NumPy handoff suite was run separately: **41 passed, one
failed** (`T34_grover_alpha_invariance`), matching the supplied report. Its
maximum discrepancy was **1.29763587e-8**, against **2e-10** absolute tolerance.

Joye's local `2409.08428v2.pdf` was consulted for the edge instrument, joint
measurement words and Section 6. Equations (6.8)--(6.13), including the complex
conjugation and coherent completion, were also checked visually on PDF page 35.
The report is version-specific; no theorem was inferred from a numerical test.

## T34 diagnosis and correction

For normalized v=S(x)omega(x),

```text
||theta(x)||² = sum_z |v_z(x)|² |omega_x(z)|²
1 - ||theta(x)||²
  = sum_z |v_z(x)|² sum_(u~z, u!=x) |omega_u(z)|².
```

The original subtractive expression loses precision when theta has norm near
one. An O(machine-epsilon) positive residual becomes an O(sqrt(epsilon))
spurious self-amplitude, explaining the approximately 1.3e-8 discrepancy.
For a star's center, all neighboring boundary spaces are one-dimensional, so
every complementary sum is structurally empty and the exact completion is zero.
Different generalized Grover parameters changed the rounding residual, not the
mathematical preparation. This was not fixed by renormalizing theta, dropping
the coherent completion or enlarging a comparison tolerance.

`core/vertex.py` now computes the nonnegative complementary-port sums with
`math.fsum` before taking the square root. This is the same mathematical model
under the already validated normalization assumptions. It gives exact structural
zeros and preserves genuine tiny mass: a regression with completion probability
1e-24 retains its 1e-12 amplitude. A stronger production T34 regression uses
1e-14 tolerance. Input validation remains unchanged.

The original oracle stays in `Material/reference_checks.py`. The independently
executable copy `tests/test_reference_handoff.py` differs only in its provenance
header and that stable completion calculation; all 42 test bodies and tolerances
are unchanged. It imports NumPy/unittest and no `sqw` production module. All 42
now pass. Run it through pytest or directly with Python. The original still
fails T34, by design, so the historical evidence remains reproducible.

## Corrections carried into tests

| Correction | Interpretation and regression |
| --- | --- |
| AUD-01 | DFT path with five vertices: transient initial mass feeds the recurrent cycle. Finite-time reference/reduced laws agree; no limiting-class solver omits this mass. |
| AUD-02 | Raw compression is TP iff every theta has norm one. A four-vertex example disproves the graph-size-only claim. |
| AUD-03 / NEW-03 | Parallel ports with coarse vertex observations can retain mixed states beyond t=2. Handoff counterexample retained; optimized eligibility excludes this extension. |
| AUD-04 | Measurement record probabilities use the full unnormalized Kraus word including X1. Exhaustive positive short records compare probabilities and normalized states. |
| AUD-05 | theta uses conjugate(omega_x(z)) from neighboring z. Tests use complex boundary vectors and nonzero beta, and check q_n versus q_n P timing. |

The direct edge channel and reference trajectories still evolve vectors/blocks
or full matrices. The added vertex reference explicitly multiplies rank-one
Kraus operators. Neither uses optimized state-ID engines. Reduced exact means
and ensemble expectations are compared to those independent operators.
Different samplers need equal laws, not identical seeded sample records.

## Preserved source SHA-256 hashes

| Source | SHA-256 |
| --- | --- |
| Material/mathematical_results.md | `70c8d89c1baac823f89c12b46857dcdcbd3449e2ba766561d4b28e54e170e07c` |
| Material/mathematical_results.json | `52ee38aa3761ec371c2ea3a2f20237ab19ac5ee7af9aa7a1a3a692b36189982f` |
| Material/reference_checks.py | `ab23054c36cf3adfd9dc3c2c454b2a08e44d87e338e630f1fd97319ded799ce9` |
| Material/validation_report.json | `d653061f1ff37084f51efc8ca3042d2000f2295d0ea3d8d49f7be7218396c0f9` |
| 2409.08428v2.pdf | `de3ccede8b943b57e87d1d89df1cba328a3011c87eabb4a67cb6aa8aa3dbb879` |

## Files in this implementation pass

- Core added: `edge_markov.py`, `vertex_markov.py`, `ensembles.py`. Updated:
  `vertex.py`, `trajectories.py`, `__init__.py` under `backend/sqw/core/`.
- API: `backend/sqw/api/app.py`, `schemas.py`.
- Interface: `frontend/src/App.tsx`, new `ResearchPanels.tsx`, `types.ts`,
  `api.ts`, `styles.css`; `i18n/index.ts`; EN/DE `app.json`, `errors.json`, new
  `research.json`. Added `__tests__/research.test.tsx`.
- Tests added: `test_reference_handoff.py`, `test_edge_markov.py`,
  `test_vertex_markov.py`, `test_ensembles.py`, `test_markov_api.py` under `tests/`.
  `test_api.py` changes its unsupported-mode example from now-enabled `vertex`
  to `unknown_walk`; the validation test remains meaningful.
- Reproduction: `examples/benchmark_markov.py`, `docs/benchmarks.json`,
  `docs/benchmarks.md`. Documentation: `AGENTS.md`, `README.md`, `docs/theory.md`,
  `architecture.md`, `mathematical_results.md`, this audit, `roadmap.md`,
  `validation.md`, and new browser evidence under `docs/screenshots/`.

## Remaining boundaries

Only finite validated simple static models are exposed. There is no multigraph,
partial-observation or time-dependent reduction. Vertex initialization still
passes through the dense reference constructor. The browser offers preset
initial states; arbitrary states are supported by Python/JSON. Stateless API
stepping replays prefixes. Graph/step/work limits bound interactive requests.
Stationary/class/period solvers and advanced spectral/RKHS/gauge analyses remain
documented research work. No remaining numerical discrepancy is known in the
tested domain; finite tests cannot establish all possible inputs.
