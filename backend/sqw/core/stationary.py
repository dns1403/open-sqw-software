"""SQW adapters for E-06/E-07 and V-04/V-05/NEW-04; no superoperators."""
import numpy as np
from .edge_markov import EdgeReduction
from .vertex_markov import VertexReduction
from .walk import ScatteringWalk
from .vertex import InducedVertexWalk
from .markov_analysis import MarkovAnalysis
from .states import checked_probabilities, validate_state


class StationaryAnalysis:
    """Cached structural analysis plus phase-sensitive atom reconstruction.

    Edge M is explicitly adapted by T=M.T to the row-stochastic generic engine.
    Vertex P is already row-stochastic. Input changes only recompute q2/r0 and
    absorption mixtures. with_beta reuses P and the entire structural result.
    """

    def __init__(self, walk, *, support_atol=1e-14, support_mask=None):
        if isinstance(walk, ScatteringWalk): walk = EdgeReduction(walk)
        if isinstance(walk, InducedVertexWalk): walk = VertexReduction(walk)
        if not isinstance(walk, (EdgeReduction, VertexReduction)):
            raise ValueError("Expected a validated edge or induced vertex model.")
        self.model = walk
        self.vertex = isinstance(walk, VertexReduction)
        self.start_step = 1 if self.vertex else 2
        self.orientation = 'row' if self.vertex else 'column'
        transition = walk.sparse_P if self.vertex else walk.sparse_M.T.tocsr()
        analytical = walk.analytic_support
        if analytical is not None and not self.vertex: analytical = analytical.T.tocsr()
        self.support_source = 'caller' if support_mask is not None else 'analytic_builtin' if analytical is not None else 'numerical'
        # Explicit masks passed to this adapter use the MODEL convention.
        if support_mask is not None and not self.vertex:
            from scipy.sparse import csr_matrix
            support_mask = csr_matrix(support_mask).T.tocsr()
        mask = analytical if support_mask is None else support_mask
        self.chain = MarkovAnalysis(transition, support_atol=support_atol, support_mask=mask)

    def initial_law(self, initial):
        if not self.vertex: return self.model.prepare_q2(initial)
        state = validate_state(initial, self.model.dimension)
        return checked_probabilities(abs(state)**2 if state.ndim == 1 else np.diag(state).real)

    def mixture(self, initial):
        return self.chain.mixture(self.initial_law(initial))

    def evolve(self, initial, steps):
        """steps is the number of reduced transitions AFTER t=1 or t=2."""
        return self.chain.evolve(self.initial_law(initial), steps, start_step=self.start_step)

    def stationary_weights(self, initial=None, *, class_index=None):
        if class_index is not None:
            if isinstance(class_index, bool) or not isinstance(class_index, (int, np.integer)) or not 0 <= class_index < len(self.chain.closed_classes):
                raise ValueError("Unknown recurrent class index.")
            return self.chain.stationary_basis.getrow(class_index).toarray().ravel()
        if initial is None: raise ValueError("An initial quantum state is needed for the absorption mixture.")
        return self.mixture(initial).stationary

    def stationary_density(self, initial=None, *, class_index=None):
        """Barycenter, not an individual conditional pure state."""
        return self.model.mean_density(self.stationary_weights(initial, class_index=class_index))

    def invariant_measure(self, initial=None, *, class_index=None):
        """Weighted atom labels, lazily reconstructed by model.atom_density.

        Vertex duplicate projectors are allowed: this is a pushforward measure,
        not a claim that labels are distinct quantum states.
        """
        q = self.stationary_weights(initial, class_index=class_index)
        labels = self.model.graph.vertices if self.vertex else range(self.model.dimension)
        return tuple((label, float(weight)) for label, weight in zip(labels, q) if weight > 0)

    def with_beta(self, beta):
        if not self.vertex: raise ValueError("beta is a vertex preparation parameter.")
        result = object.__new__(StationaryAnalysis)
        result.model = self.model.with_beta(beta)
        result.vertex, result.start_step, result.orientation = self.vertex, self.start_step, self.orientation
        result.chain, result.support_source = self.chain, self.support_source
        return result
