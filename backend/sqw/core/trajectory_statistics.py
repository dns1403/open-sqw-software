"""Phase-sensitive SQW observables and compact empirical time averages.

Sampling uses the ORIGINAL optimized reduction's transitions. The Poisson
analysis uses the explicitly reported support-policy matrix. No additional
physical measurement is introduced by evaluating an observable on an atom.
"""
from collections import OrderedDict
from dataclasses import dataclass
from numbers import Integral
from threading import RLock

import numpy as np
from .stationary import StationaryAnalysis
from .classwise_statistics import ClasswiseStatistics
from .markov_statistics import real_observable, sample_count
from .states import complex_array, validate_steps


@dataclass(frozen=True)
class TrajectoryAverage:
    samples: int
    step: int
    atom_id: int
    value: float
    mean: float
    class_index: int | None
    reference_mean: float | None
    half_width: float | None


@dataclass(frozen=True)
class EmpiricalStatistics:
    start: str
    stationary_start_requested: bool
    seed: int | None
    samples: int
    burn_in: int
    atom_start_step: int
    first_step: int
    last_step: int
    requested_class: int | None
    entered_class: int | None
    class_entry_step: int | None
    support_escape: bool
    support_sensitive: bool
    empirical_law: tuple[float, ...]
    empirical_mean: float
    confidence: float
    confidence_interval: tuple[float, float] | None
    points: tuple[TrajectoryAverage, ...]
    sampling_algorithm: str = 'direct_atom_initialization_then_original_reduced_transitions'


class TrajectoryStatistics:
    def __init__(self, walk, *, statistics=None, **support_options):
        self.stationary = walk if isinstance(walk, StationaryAnalysis) else StationaryAnalysis(walk, **support_options)
        if isinstance(walk, StationaryAnalysis) and support_options:
            raise ValueError('Support policy is already set by StationaryAnalysis.')
        self.model = self.stationary.model
        self.statistics = statistics or ClasswiseStatistics(self.stationary.chain)
        if self.statistics.chain is not self.stationary.chain:
            raise ValueError('Statistical structure does not belong to this SQW model.')
        self._observables = OrderedDict()
        self._lock = RLock()

    def _index(self, index):
        if isinstance(index,bool) or not isinstance(index,Integral) or not 0 <= index < self.model.dimension:
            raise ValueError('Observable basis index is outside the model dimension.')
        return int(index)

    def observable(self, kind='label_indicator', *, index=0, vertex=None, second=1, matrix=None, values=None):
        """Return real atom values, in the existing directed-edge/vertex order.

        outcome_indicator: 1{X_n=v}, read from the current prepared label.
        vertex_probability: Pr(X_(n+1)=v | current atom), evaluated analytically.
        coherence_real/imag: Hermitian off-diagonal physical-basis observables.
        quantum: arbitrary Hermitian A; label_values: arbitrary real f.
        """
        a = None if matrix is None else complex_array(matrix,'Observable')
        f = None if values is None else real_observable(values,self.model.dimension)
        key = (kind,index,vertex,second,None if a is None else (a.shape,a.tobytes()),None if f is None else f.tobytes())
        with self._lock:
            if key in self._observables:
                self._observables.move_to_end(key)
                return np.array(self._observables[key])
            if kind == 'label_indicator':
                f = np.zeros(self.model.dimension); f[self._index(index)] = 1
            elif kind in ('outcome_indicator','vertex_probability'):
                if isinstance(vertex,bool) or not isinstance(vertex,Integral) or vertex not in self.model.graph.vertices:
                    raise ValueError('Select a vertex in this graph.')
                if kind == 'outcome_indicator':
                    labels = self.model.graph.vertices if self.stationary.vertex else [x for x,_ in self.model.graph.directed_edges]
                    f = np.array([float(x==vertex) for x in labels])
                elif self.stationary.vertex:
                    f = self.model.sparse_P.getcol(self.model.graph.vertex_index[vertex]).toarray().ravel()
                else:
                    ids = self.model.graph.incoming_indices(vertex)
                    f = np.asarray(self.model.sparse_M[ids,:].sum(axis=0)).ravel()
            elif kind in ('coherence_real','coherence_imag','quantum'):
                if kind != 'quantum':
                    i,j = self._index(index),self._index(second)
                    if i == j: raise ValueError('Coherence requires two distinct basis indices.')
                    a = np.zeros((self.model.dimension,self.model.dimension),complex)
                    a[i,j] = 1 if kind == 'coherence_real' else -1j
                    a[j,i] = a[i,j].conjugate()
                if a is None: raise ValueError('A Hermitian observable matrix is required.')
                # Existing optimized expectation routines validate dimensions,
                # finiteness and Hermiticity, and preserve all complex phases.
                f = self.model.atom_expectations(a)
                # Inspect the imaginary roundoff explicitly without densities.
                for k in range(self.model.dimension):
                    label = self.model.graph.vertices[k] if self.stationary.vertex else k
                    ket = self.model.atom_ket(label)
                    raw = np.vdot(ket,a@ket)
                    if abs(raw.imag) > 1e-10*max(1.,float(np.max(abs(a)))):
                        raise ValueError('Hermitian observable expectation has a non-negligible imaginary part.')
            elif kind != 'label_values' or f is None:
                raise ValueError('Unknown observable or missing real label values.')
            f = real_observable(f,self.model.dimension)
            self._observables[key] = tuple(f)
            if len(self._observables)>16: self._observables.popitem(last=False)
            return f.copy()

    def analyze(self, initial, observable):
        return self.statistics.analyze(observable,self.stationary.initial_law(initial))

    def with_beta(self, beta):
        # Share only the transition-dependent Poisson factors, not phase-sensitive f.
        return TrajectoryStatistics(self.stationary.with_beta(beta),statistics=self.statistics)

    def sample(self, initial, observable, samples, *, seed=None, burn_in=0, start='experiment',
               class_index=0, confidence=.95, max_points=None):
        n, burn = sample_count(samples), validate_steps(burn_in)
        if max_points is not None and sample_count(max_points) < 2:
            raise ValueError('At least two plot points are required.')
        f = real_observable(observable,self.model.dimension)
        result = self.analyze(initial,f)
        # Validate confidence even for degenerate/transient cases.
        result.classes[0].poisson.uncertainty(n,confidence=confidence)
        q = np.asarray(result.initial_law)
        if start == 'stationary_class':
            q = self.stationary.stationary_weights(class_index=class_index)
        elif start != 'experiment': raise ValueError('Unknown statistical initialization.')
        rng = np.random.default_rng(seed)
        current = int(rng.choice(self.model.dimension,p=q))
        # Existing exact local probabilities. Never sample from thresholded T.
        transitions = []
        for i in range(self.model.dimension):
            label = self.model.graph.vertices[i] if self.stationary.vertex else i
            destinations,probabilities = self.model.transitions(label)
            if self.stationary.vertex:
                destinations = np.array([self.model.graph.vertex_index[int(x)] for x in destinations])
            transitions.append((destinations,probabilities))
        chain = self.stationary.chain
        closed = {c.class_id:c.index for c in result.classes}
        keep = set(range(n)) if max_points is None or n <= max_points else set(np.linspace(0,n-1,max_points,dtype=int))
        points,counts = [],np.zeros(self.model.dimension,dtype=int)
        average,entered,entry,escape = 0.,None,None,False
        sensitive = self.stationary.support_source=='numerical' and chain.discarded_entries>0
        for k in range(burn+n):
            physical_step = self.stationary.start_step+k
            local_class = closed.get(chain.membership[current])
            if entered is None and local_class is not None:
                entered,entry = local_class,physical_step
            elif entered is not None and local_class != entered:
                escape = True
            if k >= burn:
                count = k-burn+1
                average += (float(f[current])-average)/count
                counts[current] += 1
                if count-1 in keep:
                    theory = None if entered is None or escape else result.classes[entered].poisson
                    half = None if theory is None or sensitive else theory.uncertainty(count,confidence=confidence).half_width
                    points.append(TrajectoryAverage(count,physical_step,current,float(f[current]),average,local_class,
                        None if theory is None else theory.mean,half))
            if k < burn+n-1:
                destinations,probabilities = transitions[current]
                current = int(rng.choice(destinations,p=probabilities))
        # If a raw path leaves an analyzed closed class, remove all bands;
        # earlier classwise theory no longer describes the complete path.
        if escape:
            from dataclasses import replace
            points = [replace(p,half_width=None,reference_mean=None) for p in points]
        final_half = points[-1].half_width
        interval = None if final_half is None else (average-final_half,average+final_half)
        return EmpiricalStatistics(start,start=='stationary_class',seed,n,burn,self.stationary.start_step,
            self.stationary.start_step+burn,self.stationary.start_step+burn+n-1,
            class_index if start=='stationary_class' else None,entered,entry,escape,sensitive,
            tuple(counts/n),average,confidence,interval,tuple(points))
