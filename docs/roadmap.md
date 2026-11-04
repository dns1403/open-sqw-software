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

## Next: class-specific Poisson equations and uncertainty

Use the implemented class/absorption structure to select a recurrent class,
center observables and solve normalized Poisson equations (E-09/E-10, R-08).
State stationarity/ergodicity and periodicity assumptions before adding CLT or
confidence-interval claims. Validate asymptotic variance against independent
ensembles, and distinguish single-path uncertainty from ensemble sampling.
Sparse Vertex construction and experiment import/export are useful parallel
engineering priorities. Support-sensitivity analysis should precede numerical
claims for nearly reducible chains.

## Subsequent priorities and dependencies

1. **Scale and reproducibility:** sparse vertex construction; sampled-substream
   metadata; request cancellation within long backend jobs; versioned experiment
   import/export; custom initial-state editor; graph editing with explicit port
   migration. Current stateless playback replays prefixes.
2. **Spectral analysis:** E-08/E-11/E-12, U-02/U-03, NEW-02. Build on class/period
   diagnostics; use sparse operators, distinguish channel zero modes from
   nonzero Markov modes and cite the paper's spectral-mapping hypotheses.
3. **Poisson equations and uncertainty:** E-09/E-10 and R-08. Require a specified
   recurrent class, centered observable, stationarity/ergodicity conditions and
   justified variance estimates. Independent ensembles are already available;
   single-path CLTs are a different statistical interface.
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
