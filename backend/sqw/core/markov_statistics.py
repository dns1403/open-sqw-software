"""E-09: centered Poisson equations for finite irreducible ROW chains.

Aperiodicity is not required. This analyzes MarkovAnalysis.transition, with
its existing explicit support policy, and never changes the raw dynamics.
"""
from collections import OrderedDict
from dataclasses import dataclass
from numbers import Integral
from statistics import NormalDist

import numpy as np
from scipy.sparse import bmat, csr_matrix, diags
from scipy.sparse.linalg import splu

from .markov_analysis import MarkovAnalysis


def real_observable(values, dimension):
    array = np.asarray(values)
    if np.iscomplexobj(array) and np.any(array.imag != 0):
        raise ValueError('A real-valued observable is required for the scalar CLT.')
    array = np.asarray(array.real, dtype=float)
    if array.shape != (dimension,) or not np.all(np.isfinite(array)):
        raise ValueError('Observable must be a finite real vector in the chain ordering.')
    return array.copy()


def sample_count(value):
    if isinstance(value, bool) or not isinstance(value, Integral) or value < 1:
        raise ValueError('Sample count must be a positive integer.')
    return int(value)


@dataclass(frozen=True)
class AsymptoticUncertainty:
    samples: int
    confidence: float
    standard_error: float
    iid_comparison_standard_error: float
    half_width: float | None
    interval: tuple[float, float] | None
    approximate: bool = True
    simultaneous: bool = False


@dataclass(frozen=True)
class PoissonSolution:
    observable: tuple[float, ...]
    stationary: tuple[float, ...]
    mean: float
    centered: tuple[float, ...]
    solution: tuple[float, ...]
    period: int
    instantaneous_variance: float
    asymptotic_variance: float
    asymptotic_std: float
    degenerate: bool
    poisson_residual: float
    relative_residual: float
    centering_residual: float
    stationary_residual: float
    condition_number: float | None
    min_scaled_pivot: float
    stability_warning: bool
    variance_identity_relative_error: float

    def uncertainty(self, samples, *, empirical_mean=None, confidence=.95):
        """Pointwise CLT approximation, never a finite-N coverage guarantee.

        Degenerate or unstable solves do not produce a Gaussian interval.
        Nonstationary finite-length bias is not included in the standard error.
        """
        n = sample_count(samples)
        if not np.isfinite(confidence) or not 0 < confidence < 1:
            raise ValueError('Confidence must lie strictly between zero and one.')
        if empirical_mean is not None and (not np.isreal(empirical_mean) or not np.isfinite(empirical_mean)):
            raise ValueError('Empirical mean must be finite and real.')
        se = self.asymptotic_std / np.sqrt(n)
        half = None if self.degenerate or self.stability_warning else -NormalDist().inv_cdf((1-confidence)/2) * se
        interval = None if half is None or empirical_mean is None else (float(empirical_mean-half), float(empirical_mean+half))
        return AsymptoticUncertainty(n, confidence, float(se), float(np.sqrt(self.instantaneous_variance/n)),
                                    None if half is None else float(half), interval)


class PoissonSolver:
    """Reusable sparse bordered solve with a bounded observable-result cache.

    [L/s  1; pi  0] [h;lambda] = [g/s;0], L=I-T, s=max exit rate.
    This is equivalent to (I-T+1*pi)h=g for centered g. Building L from
    off-diagonal rates avoids cancellation in 1-T_ii for tiny exits. The
    border adds O(n) entries instead of materializing the dense rank-one term.
    """

    def __init__(self, transition, stationary=None, **support_options):
        if isinstance(transition, MarkovAnalysis):
            if support_options: raise ValueError('Support policy is already set by MarkovAnalysis.')
            chain = transition
        else:
            chain = MarkovAnalysis(transition, **support_options)
        if not chain.irreducible:
            raise ValueError('PoissonSolver requires an irreducible chain; use classwise statistics.')
        self.chain = chain
        self._t = chain.transition
        self._pi = np.asarray(chain.closed_classes[0].stationary)
        off = self._t.copy(); off.setdiag(0); off.eliminate_zeros()
        rates = np.asarray(off.sum(axis=1)).ravel()
        self._scale = float(np.max(rates)) or 1.
        self._laplacian = (diags(rates)-off).tocsr()
        if stationary is not None:
            pi = real_observable(stationary, chain.dimension)
            if np.any(pi <= 0) or abs(pi.sum()-1) > 1e-10:
                raise ValueError('Stationary law must be positive and normalized.')
            # Check scaled balance AND the unique class solution: a tiny exit
            # rate must not make an incorrect pi pass an absolute residual test.
            if np.max(abs(pi @ self._laplacian))/self._scale > 1e-10 or np.max(abs(pi-self._pi)) > 1e-9:
                raise ValueError('Supplied probability law is not stationary.')
            self._pi = pi / pi.sum()
        n = chain.dimension
        border = bmat([[self._laplacian/self._scale, csr_matrix(np.ones((n,1)))],
                       [csr_matrix(self._pi.reshape(1,n)), csr_matrix((1,1))]], format='csc')
        try:
            self._lu = splu(border)
        except RuntimeError as error:
            raise ValueError('Poisson system is numerically singular.') from error
        self._pivot = float(np.min(abs(self._lu.U.diagonal())))
        # Small diagnostic only. Sparse large systems avoid any dense n^2 copy.
        self._condition = (float(np.linalg.cond(self._laplacian.toarray()+np.outer(np.ones(n),self._pi)))
                           if n <= 128 else None)
        self._unstable = self._pivot < 1e-12 or (self._condition is not None and self._condition > 1e12)
        if self._condition is not None and not np.isfinite(self._condition): self._condition = None
        self._cache = OrderedDict()

    def solve(self, observable):
        f = real_observable(observable, self.chain.dimension)
        key = f.tobytes()
        if key in self._cache:
            self._cache.move_to_end(key)
            return self._cache[key]
        pi, t = self._pi, self._t
        # Shift first: retain small variations around a large constant offset.
        offset = f-f[0]
        shifted_mean = float(pi @ offset)
        mu = float(f[0]+shifted_mean)
        g = offset-shifted_mean
        g -= pi @ g  # centering roundoff, never changing the input observable
        with np.errstate(over='raise', invalid='raise', divide='raise'):
            try:
                h = self._lu.solve(np.r_[g/self._scale, 0.])[:-1]
                h -= pi @ h
                defect = self._laplacian @ h-g
                residual = float(np.max(abs(defect)))
                relative = residual / max(float(np.max(abs(g))), np.finfo(float).tiny)
                centered_error = float(abs(pi @ h))
                if not np.all(np.isfinite(h)) or relative > 1e-8 or centered_error > 1e-10*max(float(np.max(abs(h))),np.finfo(float).tiny):
                    raise ValueError('Poisson solve failed its residual or centering check.')
                # Equivalent nonnegative martingale variance, evaluated with
                # local shifts to avoid cancellation of h^2-(Th)^2. Genuine
                # small positive variances are never clipped to zero.
                conditional = np.zeros(len(f))
                for i in range(len(f)):
                    start,end = t.indptr[i:i+2]
                    probabilities = t.data[start:end]
                    values = h[t.indices[start:end]]
                    shifts = values-values[np.argmax(probabilities)]
                    conditional[i] = probabilities @ (shifts-probabilities @ shifts)**2
                variance = float(pi @ conditional)
                iid = float(pi @ g**2)
                identity = float(pi @ (g*(2*h-g)))
                identity_error = abs(identity-variance) / max(variance, iid, float(pi @ abs(2*g*h)), np.finfo(float).tiny)
                if not np.isfinite(variance) or variance < 0 or identity_error > 1e-8:
                    raise ValueError('Asymptotic variance failed its numerical identity check.')
            except FloatingPointError as error:
                raise ValueError('Poisson calculation overflowed; rescale the observable or inspect conditioning.') from error
        result = PoissonSolution(tuple(f), tuple(pi), mu, tuple(g), tuple(h), self.chain.closed_classes[0].period,
            iid, variance, float(np.sqrt(variance)), variance == 0., residual, relative, centered_error,
            float(np.max(abs(pi @ t-pi))), self._condition, self._pivot, self._unstable, float(identity_error))
        self._cache[key] = result
        if len(self._cache) > 16: self._cache.popitem(last=False)
        return result
