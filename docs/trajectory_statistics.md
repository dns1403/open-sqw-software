# Trajectory statistics and uncertainty

Phase 4 implements the finite real-observable Poisson/CLT contract E-09,
with E-07/V-05 class and empirical-limit conventions. R-08 supplies its scalar
finite-chain foundation; E-10/R-01 finite-atomic MMD is an optional extension.
The handoff marks these results PROVEN, using standard martingale CLTs;
E-09 is a handoff derivation, not a separately stated theorem in Joye.

For an irreducible finite row chain T and stationary pi, center f as
mu=pi@f, g=f-mu and solve (I-T)h=g with pi@h=0. Periodicity is allowed.
The implementation reuses MarkovAnalysis and its explicit support policy.
A sparse bordered system [L/s,1; pi,0] with L=I-T and s=max exit rate avoids
the dense rank-one matrix I-T+1*pi. L is formed from off-diagonal rates to
avoid cancellation in tiny exits. Sparse LU is reused; up to 16 observable
solutions are cached per solver. Supplied pi is checked against scaled balance
and the unique class stationary law, not only a small absolute residual.

The asymptotic variance sigma²=pi[h²-(Th)²] is evaluated through the equivalent
nonnegative conditional martingale variance sum_ij pi_i T_ij(h_j-(Th)_i)²,
with row-local shifts for stability. The independent identity
2*pi[g*h]-pi[g²] is checked. Positive tiny variances are never clipped; a zero
result is explicitly degenerate and gives no Gaussian confidence interval.
Deterministic cycles can have zero CLT variance but nonzero finite-length bias.

sqrt(N)(mean_N-mu) converges weakly to N(0,sigma²), including from any fixed
initial law on an irreducible class. Aperiodicity is unnecessary. The reported
sigma/sqrt(N) and normal intervals are pointwise asymptotic approximations,
not exact finite-sample or simultaneous coverage guarantees. Initial bias and
warmstart effects are not included. pi[g²]/N is shown only as an independent-
sampling comparison; successive trajectory observations are correlated.

Diagnostics include Poisson/centering/stationarity residuals, a scaled LU
pivot, and cond_2(I-T+1*pi) for dimensions <=128. Larger problems keep sparse
storage and omit the dense condition estimate. A pivot below 1e-12 or condition
number above 1e12 suppresses Gaussian intervals and raises a stability flag;
nonfinite results or failed residual checks are rejected. This is a numerical
diagnostic, not a forward-error certificate. Statistics belong to the analysis
support matrix; dropping a genuine rare transition can invalidate their use
for the original physical walk.

## Reducible chains and transient mass

`ClasswiseStatistics` reuses the stationary SCCs and absorption functions.
Each closed block gets a Poisson solver, its stationary law and period; all
classwise solutions are retained, including unreachable classes for inspection.
For input q_start, weights are a_j=q_start@h_j, including all transient mass.
Combinatorial reachability, not rounded weights, decides which classes matter.

A single path selects a class J, with empirical limit mu_J and conditional
CLT variance sigma_J². The deterministic sum a_j mu_j is the expectation of
that random limit. Its between-class variance sum a_j(mu_j-E mu_J)² persists
as N grows and must not be divided by N. Only a single reachable class enables
the global scalar CLT fields. Multiple classes always report conditional laws,
even if their means happen to coincide: unequal variances can still give a
non-Gaussian mixture. No approximate numerical equality merges these laws.
Finite transient contributions are distinct from within-class CLT noise.
## SQW observables and trajectory sampling (E-02–E-05, V-01–V-05)

`TrajectoryStatistics` uses `T=M.T` for Edge and `T=P` for Vertex. Atom
labels begin at physical time 2 and 1 respectively. Edge initialization uses
the full coherent `q2`; Vertex initialization uses the input diagonal.
`label_indicator` and `label_values` are functions of these labels.
`outcome_indicator(v)` is the already recorded outcome `1{X_n=v}`: the
target of the Edge label `(x,y)` or the Vertex preparation label x.
`vertex_probability(v)` is the analytically evaluated next Born probability
`Pr(X_(n+1)=v | current atom)`. It does not perform another measurement.

For a Hermitian A, `quantum` evaluates `Re <atom|A|atom>` and checks imaginary
roundoff. Coherence presets use `|i><j|+|j><i|` or
`-i|i><j|+i|j><i|` in the physical basis. Full complex omega and beta are
preserved. Changing beta shares classical factors but invalidates atom values.
An atomic expectation is not the noisy outcome of measuring A experimentally.

`sample(..., samples=N, burn_in=B)` records N observations, after B discarded
atom observations, at times `start+B` through `start+B+N-1`. The RNG draws
the first atom directly from q2/r0, then uses the existing original reduced
transitions. This has the correct trajectory law but need not reproduce a
sequential Edge warmstart's RNG prefix. No density history is constructed.
Downsampling only reduces returned chart points; every observation contributes
to the running mean and empirical law. Seeds affect sampling, not observables.

`start='stationary_class'` explicitly prepares an artificial stationary atom
ensemble in the selected class; it does not assert that the experimental input
was stationary. Absorption results still describe the original experimental
input. Warm-up does not certify stationarity or eliminate finite-length bias.
Conditional CLTs tolerate a finite transient prefix asymptotically; the
reported standard error does not quantify that prefix's bias.

The API `/api/statistics` bounds samples, work and dense observable dimensions.
It returns classwise diagnostics, conditional uncertainty and at most 1001
plot points. Its trajectory seed is separate from the scattering seed.
Bounded caches separate graph/coins/omega/support, beta-dependent atom values,
and observable-dependent Poisson solutions. Shared solve/observable caches are
locked. Initial states, lengths and trajectory seeds do not refactor the chain.

Sampling always uses original transitions. For numerical support with removed
entries, or if the path leaves an analyzed closed class, empirical Gaussian
bands are suppressed. Classwise theoretical values still describe the explicitly
reported analysis matrix. No support approximation silently changes physics.
