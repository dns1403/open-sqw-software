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

## Next: stationary classes, periods and absorption

Implement this before claiming asymptotic distributions (E-06/E-07, V-04/V-05,
NEW-04). Use positive-transition support to identify strongly connected and
closed recurrent classes. Compute each class's period by cycle-length gcd and
its stationary law with normalization/residual checks. Determine transient
absorption probabilities from `(I-Q)H=R`, including mass initially outside the
closed classes (AUD-01). Preserve column M versus row P orientation explicitly.

Reconstruct stationary quantum densities and label laws separately; detect
identical vertex projectors only with a justified equality criterion. Distinguish
ordinary convergence, subsequential periodic limits, Cesaro limits and empirical
occupation measures. Validate reducible identity coins, period-two paths and
the DFT five-vertex path with transient mass before adding UI claims.

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
handoff. The current pass does not implement a general stationary solver,
spectral/RKHS UI, multigraph model or cloud deployment.
