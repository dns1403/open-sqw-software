# Research roadmap

## Implemented foundation

- Validated finite simple graphs, explicit directed-edge/port order, complex
  unitaries and independent unitary/open Kraus references.
- Exact edge trajectories after two observations (E-02--E-04), coherent q2,
  sequential/direct initialization, reduced means/observables (E-05).
- Separate induced vertex trajectories/means, complex boundary conjugation,
  stable coherent completion and beta-sensitive kets (V-01/V-02/V-04/V-06).
- Compact independent-path ensembles, empirical/exact comparisons, selected
  histories, reproducible benchmarks and independent regression oracles.
- Explicit API strategies, English/German controls, playback, ensemble heatmaps
  and quantum/Markov inspection. Existing graph/matrix editing is preserved.
- Finite stationary families, SCCs/closed classes/transients, gcd periods and
  cyclic subclasses; full absorption weights including transient initial mass.
- E-06/E-07, V-04/V-05 and NEW-04 adapters with phase-sensitive barycenters,
  ordinary/Cesàro laws, TV curves and explicit numerical support policies.
- Cached structure independent of initial state/beta; bilingual Long-Time
  Dynamics graphs, sparse/full matrix inspection and exact X-04 regression.

- Sparse centered Poisson equations, stable classwise Markov variances,
  periodic-chain CLTs, transient-conditioned limits and numerical diagnostics.
- Phase-sensitive SQW observables, compact seeded time averages, explicitly
  prepared stationary ensembles, IID comparison and bilingual uncertainty UI.
- Atomic tested local commits, analytical variance regressions and reproducible
  seeded long-trajectory benchmarking (E-09; scalar part of R-08).

## Next: support sensitivity and finite-atomic MMD

Compare support thresholds and preserve genuine rare transitions before
interpreting nearly reducible long-time statistics. Add finite-atomic Gram
diagnostics and MMD (E-10/R-01/R-08), with explicit stationary initialization for
finite-length identities, periodicity and duplicate-atom qualifications.
Do not claim characteristic kernels for arbitrary measures. Sparse Vertex
construction and experiment import/export remain useful engineering priorities.

## Subsequent priorities and dependencies

1. **Scale and reproducibility:** sparse vertex construction; sampled-substream
   metadata; request cancellation within long backend jobs; versioned experiment
   import/export; custom initial-state editor; graph editing with explicit port
   migration. Current stateless playback replays prefixes.
2. **Spectral analysis:** E-08/E-11/E-12, U-02/U-03, NEW-02. Build on class/period
   diagnostics; use sparse operators, distinguish channel zero modes from
   nonzero Markov modes and cite the paper's spectral-mapping hypotheses.
3. **Finite-length uncertainty:** build on the implemented E-09 scalar CLT;
   investigate explicit bias/mixing bounds or confidence sequences only under
   appropriate hypotheses. Current pointwise asymptotic intervals do not
   guarantee finite-time or simultaneous coverage.
4. **Ensemble geometry, RKHS and MMD:** V-03/V-07, R-01--R-05/R-07. First expose
   Gram matrices and duplicate-atom handling; then kernels, moment order and
   identifiability conditions. Source V-07 is conditional. Do not infer equality
   of dynamics from equality of invariant measures.
5. **Gauge and two-time laws:** E-13--E-16, NEW-01, R-06. Depend on explicit atom
   geometry and transition kernels; distinguish invariant-measure, channel and
   dynamical equivalence. Two-time observables require joint label laws.
6. **New model contracts:** NEW-03 port multigraphs, partial observation and
   time-dependent instruments need separate types and reference channels.
   Coarse vertex measurement on parallel edges invalidates two-step purity.
   E-17 Poissonization remains conditional on its stated assumptions.

Full proof statements and qualifications stay in the immutable `Material/`
handoff. General finite stationary analysis is implemented. Full spectral/RKHS
UI, multigraph models and cloud deployment remain outside the present scope.
