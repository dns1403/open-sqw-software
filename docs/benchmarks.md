# Measured ensemble benchmarks — 4 November 2026

Reproduce from the repository root with
`python examples/benchmark_markov.py`. The script writes
[raw timings and allocation measurements](benchmarks.json), including dependency
versions, seeds and statistical deviations. This run used Windows 11,
Python 3.12.14, NumPy 2.5.4 and SciPy 1.18.1.

Each case has complex mixed input, seeded random unitary scattering, requested
state/vertex/edge/exact statistics and three selected histories. Vertex cases
use uniform omega and beta_x=0.23x. Runtime is the median of three uninstrumented
`perf_counter` runs. Model and initial-state construction are excluded; per-run
reduction setup and result construction are included. No API/JSON/browser cost
is included. Memory is a **separate tracemalloc peak**, excluding the prebuilt
model/input; it is not RSS or a measure of all native-library allocations.

| Model / graph | Hilbert dimension | Paths × steps | Reference time | Optimized time | Reference peak MiB | Optimized peak MiB |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Edge / cycle 8 | 16 | 300 × 20 | 0.357399 s | 0.006241 s | 0.412 | 0.088 |
| Edge / star 10 | 18 | 300 × 20 | 0.385590 s | 0.006803 s | 0.517 | 0.101 |
| Vertex / cycle 8 | 8 | 300 × 20 | 0.216041 s | 0.004479 s | 0.129 | 0.059 |
| Vertex / star 10 | 10 | 300 × 20 | 0.219035 s | 0.004782 s | 0.184 | 0.062 |
| Edge / cycle 32 | 64 | 50000 × 40 | not measured | 0.096242 s | not measured | 1.725 |

The larger run measures the optimized implementation only; no reference speedup
is claimed for it. Hardware load and library versions can change these numbers.
The streamed reference already avoids storing all paths, so the comparison
does not use an artificially unbounded reference implementation.

Independent dense Kraus means were compared with reduced densities at t=0..8
for all five configurations. The maximum absolute matrix-entry discrepancy was
**8.326672684688674e-16**. This deterministic numerical agreement is separate
from Monte Carlo error: the 50000-path run's final vertex Born TV deviation was
**0.00806146**, and its label-law TV was **0.01340151**. Different samplers have
different draws even with the same seed, so empirical results are not expected
to match element for element. Mathematical invariants and statistical bounds
are tested separately in the regression suite.
