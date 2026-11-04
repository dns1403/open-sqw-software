# Roadmap

## Implemented

- **P0:** installable Python library; deterministic graph basis; local unitary
  matrices; sparse global operator; exact open edge channel; mathematical tests.
- **P1:** FastAPI/Pydantic; React/Vite; Cytoscape vertex selection; matrix editing;
  basis/uniform initial states; unitary/open evolution; Plotly distributions,
  step controls and history.
- **P2:** general pure/mixed reference trajectories with seeds, measurement
  probabilities and conditional states; individual trajectories in the API/UI;
  exact and statistical ensemble comparisons in tests.
- **P3 partial:** independent Section-6 Python vertex channel with complex omega
  vectors, phases, boundary operator and Kraus/Markov diagnostics.
- **Internationalization:** English-first, complete English/German presentation,
  persistent explicit preference, locale-aware observables, state-preserving
  switching, translated validation and stable API error descriptors.

## Next research step

Record the additional theorems in `mathematical_results.md`, check their
hypotheses and implement a separate Markov/pure-state strategy behind
`TrajectoryEngine`. Validate it against the direct reference for arbitrary
admissible initial density matrices. The first two measurements and the exact
time convention deserve particular attention.

## Further development

1. Streaming ensembles with uncertainty bands and reproducible independent RNG
   substreams; compare exact quantum and classical dynamics.
2. Separate vertex experiment contract and controls for omega/beta, suitable
   initial states and comparison views.
3. Graph editor with an explicit policy for changed neighbor orderings and
   invalidated scattering matrices; never silently reorder experiments.
4. Versioned experiment format containing graph basis, matrices, initial state,
   strategy, seed, dependency versions and result metadata.
5. Spectral analysis using optional small reference matrices or matrix-free
   operators; stationary states and asymptotic boundary cases.
6. Larger graphs, resource management and public operation only when needed.
   Hosting, authentication and a database are not currently necessary.

A mode is complete only when its core, tests, contract and controls work together.
Until then, the corresponding interface control remains disabled. Additional
languages can extend the existing resource namespaces without changing the
simulation contract.
