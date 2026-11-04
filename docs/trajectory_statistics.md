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
