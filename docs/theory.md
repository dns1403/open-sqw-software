# Mathematical conventions and reference methods

Reference: Alain Joye, *Unitary and Open Scattering Quantum Walks on Graphs*,
[arXiv:2409.08428v2](https://arxiv.org/abs/2409.08428v2), especially Sections 2,
4 and 6. The PDF included in this repository is the authoritative version.

## Graph and basis

We consider finite, connected, simple undirected graphs with at least two
vertices. Multiple edges, self-loops and disconnected components are rejected.
Vertices use integer labels, not array positions. The vertex order and each
neighbor order are sorted increasingly. `size` is the total vertex count for
all presets; a star with `size = n` has `n - 1` leaves and center `0`.

Each edge produces two basis states. **`(x, y)` and `|xy⟩` mean from `y` to `x`.**
The basis is ordered first by target `x`, then by source `y`. For the path
`0 - 1 - 2`, it is

```text
index     0       1       2       3
state   |01⟩    |10⟩    |12⟩    |21⟩
arrow    1→0     0→1     2→1     1→2
```

`GraphModel.edge_index` is the authoritative mapping. The dimension is
`D = 2|E|`. The incoming spaces and projectors are

\[
\mathcal H_x^I=\operatorname{span}\{|xy\rangle:y\sim x\},\qquad
P_x^I=\sum_{y\sim x}|xy\rangle\langle xy|.
\]

## Local and global unitary dynamics

Rows of `S(x)` index outgoing neighbors `z`, columns index incoming neighbors
`y`; both use exactly `graph.neighbors[x]`. Equation (2.5) is implemented:

\[
U_S|xy\rangle=\sum_{z\sim x}S_{zy}(x)|zx\rangle.
\]

Since each local matrix is unitary and the incoming and outgoing spaces each
form orthogonal decompositions, `U_S` is unitary as well (Lemma 2.3).
The global operator is stored as a sparse SciPy matrix. Direct pure-state
evolution requires a state vector, not a superoperator.

Presets are `identity = I`, `grover = 2J/d - I`, the real Hadamard operator
`[[1,1],[1,-1]]/sqrt(2)` only for degree 2, the normalized discrete Fourier
matrix, and random unitary matrices from complex Gaussian QR with phase
correction. The Fourier convention is specified in the function docstring.
All local matrices are checked for dimensions, finite entries and unitarity.
Identity scattering reflects a directed basis state at its target back toward
its source.

For normalized vectors, `psi[n+1] = U_S psi[n]`. Edge probabilities are
`abs(psi)**2`; for density matrices they are the diagonal entries. The displayed
vertex distribution is always the **incoming target marginal**

\[
q_n(x)=\operatorname{tr}(P_x^I\rho_n)
      =\sum_{y\sim x}\rho_n[(x,y),(x,y)].
\]

It is not an induced vertex-walk dynamics.

## Open edge walk

Equations (4.8), (4.12) and (4.15) give

\[
K_x=U_SP_x^I,\qquad
\Phi_S(\rho)=\sum_x K_x\rho K_x^\dagger
=U_S\Bigl(\sum_xP_x^I\rho P_x^I\Bigr)U_S^\dagger.
\]

Both `sum K_x† K_x = I` and `sum K_x K_x† = I` hold: the channel is completely
positive, trace preserving and unital. It removes coherences **between** incoming
vertex spaces before scattering. Coherences within an incoming space remain.
The reference processes local density blocks directly and does not construct a
`D² × D²` superoperator. Its states are still dense `D × D` matrices. This is a
reference for small systems, not a claim of efficient large-graph simulation.

## Quantum trajectories and time indices

The reference implements the conditional evolution of Section 4.2 for both pure
initial vectors and mixed initial density matrices. For `j = 0, ..., steps - 1`:

1. `states[j]` is `rho_j` **after** the previous scattering, or the specified
   initial state when `j = 0`.
2. `probabilities[j][i] = tr(P_x^I rho_j)`, where `x = graph.vertices[i]`, is
   the distribution of the next outcome `X_(j+1)`.
3. `outcomes[j] = X_(j+1)` is sampled from this Born distribution;
   `selected_probabilities[j]` records its conditional probability.
4. `reduced_states[j] = P_x^I rho_j P_x^I / p_x` is the normalized state
   **after measurement and before scattering**.
5. `states[j+1] = U_S reduced_states[j] U_S†` is `rho_(j+1)`.

Pure states instead reduce to `P_x^I psi_j / sqrt(p_x)` and are multiplied by
`U_S`. The output retains the input representation. For `steps = 0`, only
`states[0]` exists and all measurement lists are empty. A realized path has
probability equal to the product of its recorded conditional probabilities.
Exactly zero-probability outcomes are never sampled.

Each reference trajectory has its own `numpy.random.Generator`. New engines
with the same seed and inputs reproduce the same results; repeated calls to
one engine advance its stream. Bitwise reproducibility depends on the NumPy
version. The stateless API creates an engine for each request, so step requests
with the same seed reproduce identical prefixes.

The ensemble expectation is exactly `E[rho_n] = Phi_S^n(rho_0)` (Proposition 4.8).
Tests compare full Monte Carlo ensemble density matrices with statistical error
bounds and independently compare the exact weighted sum of all short measurement
paths with the channel.

## Exact edge reduction (E-02 through E-05)

On the validated simple loopless graph with static unitaries and every incoming
vertex measurement observed, at n >= 2 the conditional state is
`sigma_(X_n,X_(n-1)) = |eta><eta|`, where `eta_xy = U|xy>`.
An edge ID labels this generally coherent scattered state, not an occupied basis
edge. A mixed input can remain mixed at t=1. This assertion does not imply that
the mean state becomes pure.

With `A_y = rho0[I_y,I_y]`, the full first-pair law is

```text
q2[(x,y)] = (S(y) @ A_y @ S(y)†)[port(x),port(x)]
         = Pr(X1=y, X2=x).
M[(z,x),(x,y)] = |S(x)[port(z),port(y)]|²
q_n = M^(n-2) @ q2                      (column-stochastic convention)
mean_rho_n = U @ diag(q_n) @ U†
nu_n = sum_e q_n[e] delta_(sigma_e)
```

Discarding off-diagonal entries of `A_y` changes the experiment. The sequential
online engine samples X1, keeps the normalized scattered local block, then
samples X2. The direct batch initializer samples `(X2,X1)` from q2 and reconstructs
both stages. It has the same joint law but may consume a different random stream.
Queries, explicit conditioning and reconstruction do not consume random draws.

The physical post-scattering edge Born distribution is **M @ q_n**. Its target
marginal gives the next vertex measurement probabilities. A past outcome count,
a preparation-label count and this Born distribution are distinct statistics.
For a Hermitian A, precompute `a[e]=<eta_e|A|eta_e>` and evaluate `q_n @ a`.
Since the edge atoms are orthogonal, mean purity is `q_n @ q_n`.
Local multiplication by `|S(x)|²` needs no dense M or density matrix. The direct
Kraus reference remains independent of this reduction.

Parallel ports with coarse vertex measurements, partial observations, different
instruments and changing coins do not satisfy this contract. The eligibility
checks reject them; the current graph model itself rejects multigraphs.

## Independent induced vertex walk

Section 6 defines a channel on `l²(V)`, not `l²(D)`. With normalized local vectors
`omega(x)` in the incoming neighbor basis,

\[
R=\sum_x|x\rangle\langle\omega(x)|,\qquad RR^\dagger=I_V,
\]
\[
v_z(x)=(S(x)\omega(x))_z,\quad
\theta_z(x)=\overline{\omega_x(z)}\,v_z(x),
\]
\[
\chi(x)=\theta(x)+e^{i\beta_x}\sqrt{1-\|\theta(x)\|^2}|x\rangle,
\quad G_x=|\chi(x)\rangle\langle x|,
\quad\Psi_S(\rho)=\sum_xG_x\rho G_x^\dagger.
\]

The conjugated coefficient in `theta` is essential: it comes from the bra in
`R` (equations (6.8)-(6.11), visually checked against PDF page 35 during the
initial implementation). Because the graph has no self-loops, `theta(x)` and
`|x⟩` are orthogonal. Completing `theta(x)` to `chi(x)` restores normalization
and trace preservation. Plain compression `R Phi_S(R† rho R) R†` is generally
only trace nonincreasing and is not presented as the completed vertex channel.

The vertex core accepts arbitrary normalized `omega` and finite real phases
`beta`; defaults are `omega_y(x)=1/sqrt(d_x)` and `beta_x=0`.
The row-stochastic matrix is `P[x,y] = |chi(x)[y]|²`; classical distributions
are row vectors evolving as `p_next = p @ P`. Direct Kraus evolution remains
the implemented quantum reference.

## Exact vertex reduction (V-01, V-02, V-04, V-06)

At n >= 1 the conditional state is `tau_(X_n)=|chi(X_n)><chi(X_n)|`. With
`r0=diag(rho0)` (or squared moduli of a pure vector),

```text
q_n = r0 @ P^(n-1)          # current preparation-label law
mean_rho_n = sum_x q_n[x] tau_x
born_vertices_n = q_n @ P   # next position measurement
```

Initial off-diagonal terms disappear in the first vertex measurement, unlike
the edge incoming blocks. No extra transition is applied when initializing q1.
Vertex atoms may be nonorthogonal or identical; label counts are retained without
approximate merging. Mean purity is therefore not generally `q_n @ q_n`.
Sparse chi columns and P support lazy reconstruction, local transitions and
phase-sensitive observable expectations. Changing beta leaves P invariant and
updates the quantum kets; `VertexReduction.with_beta` explicitly reuses P.
Bistochastic P does not imply that the quantum channel is unital.

For numerical stability, the completion coefficient is evaluated using the
equivalent nonnegative identity

```text
1 - ||theta(x)||² = sum_(z~x) |v_z(x)|² sum_(u~z, u!=x) |omega_u(z)|².
```

Normalized v and omega imply this identity. It avoids cancellation near zero
and the amplification of an O(epsilon) residual by a square root. No tolerance
was enlarged and no small physical completion is zeroed. See the T34 audit.
Raw compression is trace preserving exactly when every theta has norm one;
graph size alone does not decide this. Transient initial mass contributes to
eventual recurrent-class weights through absorption probabilities. Stationary
and limit diagnostics are deferred until that contribution and periods are handled.

## Numerics and limits

Operators and states use complex double precision. Validation uses an explicit
absolute tolerance, without an implicit large relative tolerance. Incorrect
norms or traces, non-Hermitian inputs and nonpositive inputs are rejected rather
than normalized or projected. Very small negative probabilities at roundoff
scale may be clipped to zero only after state validation so that discrete
sampling remains well defined. This is not a physical correction.

Reference tests generally use `1e-12` for small analytic examples and `1e-10`
for accumulated operations. Statistical tests use separate bounds derived from
ensemble size and variance. Independent-path ensembles retain compact labels,
requested counts and Born averages; selected histories are optional. These are
ensemble laws at fixed times, not occupation measures of a single long path.
Spectral and asymptotic analyses remain separate extensions. Numerical agreement
supports implementation validation; it does not prove the mathematical results.

## Presentation languages

English/German localization affects labels and formatted observable values only.
It never changes any equation, basis entry, scattering matrix, numerical state,
random seed, transition probability or model identifier described above. Matrix
JSON retains its standard numeric syntax in both languages. Selecting a language
does not run a simulation or change an existing trajectory.
