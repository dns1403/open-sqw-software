"""Finite ROW-stochastic structural analysis (E-06/E-07, V-04/V-05).

Support is an explicit modelling decision: declared masks certify zeros by
caller knowledge; otherwise a probability cutoff is a numerical convention.
The raw validated matrix is retained for finite-time curves and residuals.
The separately exposed analysis matrix removes excluded entries and rescales
rows. Its infinite-time classification is not a theorem about omitted rates.
"""
from collections import deque
from dataclasses import dataclass
from math import gcd
import warnings

import numpy as np
from scipy.sparse import csr_matrix, diags, eye, issparse
from scipy.sparse.csgraph import connected_components
from scipy.sparse.linalg import MatrixRankWarning, spsolve

from .states import checked_probabilities, validate_steps


@dataclass(frozen=True)
class CommunicatingClass:
    id: int
    states: tuple[int, ...]
    closed: bool
    period: int | None  # no return cycle in a transient acyclic singleton
    cyclic_subclasses: tuple[tuple[int, ...], ...]
    stationary: tuple[float, ...] | None  # local order, only closed classes
    residual: float | None
    raw_residual: float | None


@dataclass(frozen=True)
class InitialAsymptotics:
    class_weights: np.ndarray  # closed_classes order
    stationary: np.ndarray
    ordinary_guaranteed: bool
    reachable_periods: tuple[int, ...]


@dataclass(frozen=True)
class MarkovEvolutionFrame:
    step: int
    probabilities: np.ndarray
    cesaro: np.ndarray
    total_variation: float
    cesaro_total_variation: float


def _maxabs(value):
    array = value.data if issparse(value) else np.asarray(value)
    return float(np.max(abs(array), initial=0))


def _solve(a, b):
    with warnings.catch_warnings():
        warnings.simplefilter("error", MatrixRankWarning)
        try:
            result = np.asarray(spsolve(a.tocsc(), b)).reshape(np.shape(b))
        except (MatrixRankWarning, RuntimeError, ValueError) as error:
            raise ValueError("Stationary/absorption solve is numerically singular.") from error
    if not np.all(np.isfinite(result)) or _maxabs(a @ result - b) > 1e-9:
        raise ValueError("Stationary/absorption solve failed its scaled residual check.")
    return result


class MarkovAnalysis:
    """Reusable SCC, period, stationary-family and absorption analysis.

    Input uses row sources and column destinations. No orientation inference.
    support_mask, when supplied, is a caller-declared exact positive support;
    it preserves tiny positive transitions even below support_atol. Excluded
    entries must be <= validation_atol. Otherwise entries <= support_atol are
    excluded, with the discarded mass explicitly reported. The input is never
    changed. Sparse solves avoid inverses and arbitrary degenerate eigenvectors.
    """

    def __init__(self, transition, *, support_atol=1e-14, support_mask=None,
                 validation_atol=1e-10):
        if not np.isfinite(validation_atol) or not 0 < validation_atol < 1:
            raise ValueError("validation_atol must be finite and between zero and one.")
        if not np.isfinite(support_atol) or not 0 <= support_atol < 1:
            raise ValueError("support_atol must be finite and between zero and one.")
        source = csr_matrix(transition, copy=True)
        if source.dtype.kind == 'c' and np.any(source.data.imag != 0):
            raise ValueError("Transition probabilities must be real.")
        p = source.real.astype(float)
        p.sum_duplicates(); p.eliminate_zeros(); p.sort_indices()
        n, m = p.shape
        if not n or n != m or not np.all(np.isfinite(p.data)) or np.any(p.data < 0):
            raise ValueError("Transition matrix must be finite, nonnegative, nonempty and square.")
        totals = np.asarray(p.sum(axis=1)).ravel()
        self.row_residual = _maxabs(totals - 1)
        if self.row_residual > validation_atol:
            raise ValueError("Transition matrix must be row stochastic within validation_atol.")
        self.dimension = n
        self.validation_atol = validation_atol
        self.support_atol = float(support_atol)
        self._raw = p.copy()
        if support_mask is not None:
            mask = csr_matrix(support_mask)
            mask.sum_duplicates(); mask.eliminate_zeros()
            if mask.shape != p.shape or not np.all((mask.data == 0) | (mask.data == 1)):
                raise ValueError("Support mask must be a boolean matrix with matching shape.")
            mask = mask.astype(bool)
            if mask.nnz != p.multiply(mask).nnz:
                raise ValueError("Declared positive support includes a zero transition.")
            effective = p.multiply(mask).tocsr()
            if _maxabs(p - effective) > validation_atol:
                raise ValueError("Declared zeros disagree with probabilities beyond validation_atol.")
            self.support_policy = "declared_mask"
        else:
            effective = p.copy()
            effective.data[effective.data <= support_atol] = 0
            effective.eliminate_zeros()
            self.support_policy = "stored_positive" if support_atol == 0 else "numerical_threshold"
        discarded = p - effective
        self.discarded_entries = int(discarded.nnz)
        self.discarded_max_probability = _maxabs(discarded)
        self.discarded_max_row_mass = _maxabs(discarded.sum(axis=1))
        sums = np.asarray(effective.sum(axis=1)).ravel()
        if np.any(sums <= 0):
            raise ValueError("Support policy removed every transition in a row.")
        self._transition = (diags(1 / sums) @ effective).tocsr()
        self._transition.sort_indices()
        self.matrix_change_max_row_l1 = _maxabs(abs(self._transition - p).sum(axis=1))
        self.column_residual = _maxabs(np.asarray(p.sum(axis=0)).ravel() - 1)
        self.bistochastic = self.column_residual <= validation_atol
        support = self._transition.copy()
        support.data = np.ones_like(support.data)
        self._support = support
        _, labels = connected_components(support, directed=True, connection='strong')
        buckets = {}
        for state, label in enumerate(labels): buckets.setdefault(int(label), []).append(state)
        components = sorted((tuple(states) for states in buckets.values()), key=lambda c: c[0])
        membership = np.empty(n, dtype=int)
        for i, states in enumerate(components): membership[list(states)] = i
        self.membership = tuple(int(x) for x in membership)
        classes = []
        for i, states in enumerate(components):
            outgoing = support[list(states)].indices
            closed = bool(np.all(membership[outgoing] == i))
            period, cyclic = self._period(states)
            pi, residual, raw_residual = None, None, None
            if closed:
                block = self._transition[list(states)][:, list(states)]
                pi = self._stationary(block)
                full = csr_matrix((pi, (np.zeros(len(states), dtype=int), states)), shape=(1, n))
                residual = _maxabs(full @ self._transition - full)
                raw_residual = _maxabs(full @ self._raw - full)
            classes.append(CommunicatingClass(i, tuple(int(x) for x in states), closed,
                period, cyclic, None if pi is None else tuple(float(x) for x in pi), residual, raw_residual))
        self.classes = tuple(classes)
        self.closed_classes = tuple(c for c in classes if c.closed)
        self.transient_states = tuple(x for c in classes if not c.closed for x in c.states)
        self.irreducible = len(classes) == 1
        self.unique_stationary = len(self.closed_classes) == 1
        self.ordinary_for_all_initials = all(c.period == 1 for c in self.closed_classes)
        rows, cols, data = [], [], []
        for j, c in enumerate(self.closed_classes):
            rows.extend([j] * len(c.states)); cols.extend(c.states); data.extend(c.stationary)
        self._stationary_basis = csr_matrix((data, (rows, cols)), shape=(len(self.closed_classes), n))
        self._absorption = self._absorption_functions()

    @property
    def transition(self):
        """Detached analysis matrix (thresholded/masked and row-normalized)."""
        return self._transition.copy()

    @property
    def raw_transition(self):
        return self._raw.copy()

    @property
    def stationary_basis(self):
        """Rows are extreme stationary laws, in closed_classes order."""
        return self._stationary_basis.copy()

    @property
    def absorption(self):
        """H[x,j] = eventual probability of entering closed class j."""
        return self._absorption.copy()

    def _period(self, states):
        allowed = set(states)
        depth = {states[0]: 0}; queue = deque([states[0]])
        edges = []
        while queue:
            x = queue.popleft()
            row = self._support.indices[self._support.indptr[x]:self._support.indptr[x+1]]
            for y in row:
                if y not in allowed: continue
                edges.append((x, y))
                if y not in depth:
                    depth[y] = depth[x] + 1; queue.append(y)
        period = 0
        for x, y in edges: period = gcd(period, abs(depth[x] + 1 - depth[y]))
        if not period: return None, ()
        cyclic = tuple(tuple(int(x) for x in states if depth[x] % period == k) for k in range(period))
        return period, cyclic

    @staticmethod
    def _stationary(block):
        size = block.shape[0]
        if size == 1: return np.ones(1)
        # Construct P-I from OFF-diagonal rates, avoiding cancellation when
        # a genuine exit rate is far below the spacing of floats near one.
        off = block.copy(); off.setdiag(0); off.eliminate_zeros()
        rates = np.asarray(off.sum(axis=1)).ravel()
        generator = (off - diags(rates)).T.tocsr()
        scaled = generator / float(np.max(rates))
        a = scaled.tolil(); a[-1, :] = np.ones(size)
        b = np.zeros(size); b[-1] = 1
        pi = _solve(a.tocsr(), b)
        if _maxabs(scaled @ pi) > 1e-9:
            raise ValueError("Stationarity failed the scaled balance residual check.")
        return checked_probabilities(pi, atol=1e-9)

    def _absorption_functions(self):
        n, r = self.dimension, len(self.closed_classes)
        rows, cols, values = [], [], []
        for j, c in enumerate(self.closed_classes):
            rows.extend(c.states); cols.extend([j] * len(c.states)); values.extend([1.] * len(c.states))
        transient = list(self.transient_states)
        if transient:
            p = self._transition
            off = p.copy(); off.setdiag(0); off.eliminate_zeros()
            rates = np.asarray(off[transient].sum(axis=1)).ravel()
            # Embedded jump chain: row scaling removes tiny exit rates without
            # changing absorption probabilities. No explicit inverse.
            scale = diags(1 / rates)
            a = eye(len(transient), format='csr') - scale @ off[transient][:, transient]
            b = np.column_stack([np.asarray(p[transient][:, list(c.states)].sum(axis=1)).ravel()
                                 for c in self.closed_classes]) / rates[:, None]
            answer = np.asarray(_solve(a, b)).reshape(len(transient), r)
            if np.any(answer < -1e-9) or np.any(answer > 1 + 1e-9) or _maxabs(answer.sum(axis=1) - 1) > 1e-9:
                raise ValueError("Absorption probabilities failed positivity/normalization checks.")
            answer = np.clip(answer, 0, 1)
            ri, cj = np.nonzero(answer)
            rows.extend(np.asarray(transient)[ri]); cols.extend(cj); values.extend(answer[ri, cj])
        h = csr_matrix((values, (rows, cols)), shape=(n, r))
        self.absorption_residual = _maxabs(self._transition @ h - h)
        self.absorption_raw_residual = _maxabs(self._raw @ h - h)
        return h

    def _initial(self, initial):
        q = checked_probabilities(initial)
        if q.shape != (self.dimension,): raise ValueError("Initial law has the wrong dimension.")
        return q

    def mixture(self, initial):
        q = self._initial(initial)
        weights = checked_probabilities(np.asarray(q @ self._absorption).ravel(), atol=1e-9)
        stationary = checked_probabilities(np.asarray(weights @ self._stationary_basis).ravel())
        periods = tuple(c.period for c in self.reachable_closed_classes(q))
        return InitialAsymptotics(weights, stationary, all(p == 1 for p in periods), periods)

    def reachable_closed_classes(self, initial):
        """Graph reachability, without thresholding small absorption weights."""
        q = self._initial(initial)
        reached = set(int(x) for x in np.flatnonzero(q > 0)); todo = list(reached)
        while todo:
            x = todo.pop()
            for y in self._support.indices[self._support.indptr[x]:self._support.indptr[x+1]]:
                if int(y) not in reached: reached.add(int(y)); todo.append(int(y))
        return tuple(c for c in self.closed_classes if c.states[0] in reached)

    def evolve(self, initial, steps, *, start_step=0, use_analysis_matrix=False):
        """Include q_start and average q_start,...,q_n; raw curves by default.

        The stationary reference belongs to the support-policy analysis matrix.
        Periodic classes only deny an all-input guarantee: a stationary input
        still converges. No conclusion is drawn from a flat finite-time chart.
        """
        q = self._initial(initial)
        count, start = validate_steps(steps), validate_steps(start_step)
        reference = self.mixture(q).stationary
        p = self._transition if use_analysis_matrix else self._raw
        average = np.zeros_like(q)
        for k in range(count + 1):
            average += (q - average) / (k + 1)
            yield MarkovEvolutionFrame(start + k, q.copy(), average.copy(),
                float(abs(q - reference).sum() / 2), float(abs(average - reference).sum() / 2))
            if k < count: q = checked_probabilities(np.asarray(q @ p).ravel(), atol=self.validation_atol)
