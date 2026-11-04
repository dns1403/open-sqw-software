# Mathematical results and implementation mapping

The 4 November 2026 handoff contains **39 results**. Complete statements,
proofs, assumptions and test references remain unchanged in
[Material/mathematical_results.md](../Material/mathematical_results.md) and
[its JSON specification](../Material/mathematical_results.json). The numerical
oracle and original validation report also remain unchanged. Read the
[audit](mathematical_audit.md) for the T34 correction and source hashes.

Source statuses are provenance, not an assertion that software proves a theorem:
`PROVEN` denotes the handoff derivation; `PAPER_THEOREM` cites the paper;
`CONDITIONAL` retains explicit extra hypotheses. Of 39 entries, U-03 is
`PAPER_THEOREM`, E-17 and V-07 are `CONDITIONAL`; the other 36 are `PROVEN` in
the supplied specification. Integration status below is separate.

## Implemented mathematical contracts

| IDs | Contract and scope | Implementation | Independent validation |
| --- | --- | --- | --- |
| U-01 | Local complex unitaries and explicit arc flip; pure/mixed evolution | `core/walk.py`, `scattering.py` (existing) | existing walk tests, handoff oracle |
| E-01 | Measurement-before-scattering Kraus channel and block coherences | `core/walk.py`, `trajectories.py` (retained) | existing channel tests; full Kraus-word comparisons |
| E-02 | Conditional purification at t=2 on SIMPLE_STATIC, not at t=1 for all mixed inputs | `EdgeConditionalState`, `EdgeSession` | `test_edge_markov.py`: mixed warmstart, exhaustive words |
| E-03 | Coherent q2; column M; joint first-pair law; sequential and direct samplers | `EdgeReduction`, `OptimizedEdgeTrajectory` | full Kraus paths, direct q2 law, phase/coherence examples |
| E-04 | Current edge atom determined by the last two observed vertices | compact atom IDs and reconstruction | positive-path replay and zero-probability branches |
| E-05 | Reduced means, state laws, Born Mq and Hermitian observables | `EdgeMeanState`, local `apply_M`, ensembles | full density and observable comparisons through t=8 |
| V-01 | Conjugated neighboring omega and coherent chi completion | `core/vertex.py`; stable complementary-port mass | complex boundary tests, T34, tiny nonzero completion |
| V-02 | Rank-one preparation after t=1, row P, q1=diag(rho0) | `VertexReduction`, `OptimizedVertexTrajectory` | `test_vertex_markov.py`, independent `ReferenceVertexTrajectory` |
| V-03 (partial) | Retain labels when atoms coincide; no approximate merging | ensemble label counts and UI explanation | handoff oracle; quotient/lumping solver deferred |
| V-04 (finite-time part) | q_n=r0 P^(n-1), physical mean and Born q_n P | `VertexMeanState`, sparse `apply_P` | independent Kraus means and timing checks; stationary solver deferred |
| V-06 (phase part) | P invariant under beta; phase-sensitive states change | `VertexReduction.with_beta` reuses P | beta cache/state checks; no bistochastic=>unital assumption |
| AUD-01--05; NEW-03 restriction | Transient mass, raw compression criterion, port counterexample, joint normalization, complex conjugation | eligibility checks, stable construction, documented restrictions | `test_vertex_markov.py`, `test_edge_markov.py`, handoff oracle |

The modules live under `backend/sqw/`. `tests/test_reference_handoff.py` retains
all 42 oracle test bodies and tolerances with one documented numerical construction
correction. It imports no production code. Backend/API tests also use independent
dense Kraus products; the frontend never implements the physics.
`tests/test_markov_api.py` checks serialization, stages and strategies;
`tests/test_ensembles.py` checks statistics and compact selected histories.

## Preserved research results, deferred product features

| IDs | Subject | Dependency / implementation status |
| --- | --- | --- |
| U-02, U-03 | Unitary time means and spectral mapping | Reference oracle only; spectral interface deferred |
| E-06, E-07 | Stationary measures and types of convergence | Next: recurrent classes, periods and absorption |
| E-08 | Channel spectrum, zero modes and product purification | Requires spectral diagnostics; oracle only |
| E-09, E-10 | Poisson equation, CLT and empirical RKHS errors | Requires class-specific stationary analysis |
| E-11, E-12 | Mixing, flat coins, entropy and resistance | Support/period diagnostics before mixing claims |
| E-13, E-14, E-15, E-16 | Invariant ensembles, dynamics, two-time laws, reversal | Geometry and joint-law analysis deferred |
| E-17 | Poissonization and Isom assumptions | Conditional source result; no new engine enabled |
| V-04, V-05, NEW-04 | Stationarity, transients and convergence | Finite-time means implemented; asymptotic solver deferred |
| V-06, V-07 | Unitality, frames and stabilizers | Phase part implemented; frame/stabilizer analysis deferred; V-07 conditional |
| R-01--R-08 | Tensor kernels, MMD, moments, identifiability, two-time and fluctuation analysis | Oracle examples only; no RKHS feature presented as complete |
| NEW-01, NEW-02 | Channel gauges, ranks and perturbation bounds | Oracle examples only; analysis deferred |
| NEW-03 | Port multigraphs and failure of universal purification | Counterexample tested; actual port graph model deferred |

See the [prioritized roadmap](roadmap.md) for prerequisites and exceptional cases.

## Template for future entries

Keep a stable ID, title, provenance/date, notation, complete hypotheses, full
statement, proof or precise reference, source proof status, implementation
status, numerical consequences and cost, independent validation requirements,
and explicit limitations. Preserve source material and record corrections
transparently. A passing test is evidence about an implementation, not a proof.
