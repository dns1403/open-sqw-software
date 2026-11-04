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

After two measurement/scattering steps on a simple graph, conditional edge states
belong to a family of pure scattered states: consecutive vertex outcomes identify
the intervening directed edge. This motivates future Markov methods. The reference
algorithm does not use that reduction. New strategies must state their hypotheses
and be validated against the reference, including complex coherences.

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

## Numerics and limits

Operators and states use complex double precision. Validation uses an explicit
absolute tolerance, without an implicit large relative tolerance. Incorrect
norms or traces, non-Hermitian inputs and nonpositive inputs are rejected rather
than normalized or projected. Very small negative probabilities at roundoff
scale may be clipped to zero only after state validation so that discrete
sampling remains well defined. This is not a physical correction.

Reference tests generally use `1e-12` for small analytic examples and `1e-10`
for accumulated operations. Statistical tests use separate bounds derived from
ensemble size and variance. Large ensembles, spectral analyses and new mathematical
reductions are separate extensions, not part of the reference channel definition.

## Presentation languages

English/German localization affects labels and formatted observable values only.
It never changes any equation, basis entry, scattering matrix, numerical state,
random seed, transition probability or model identifier described above. Matrix
JSON retains its standard numeric syntax in both languages. Selecting a language
does not run a simulation or change an existing trajectory.
