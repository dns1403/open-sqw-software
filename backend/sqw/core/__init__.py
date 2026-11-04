"""Public mathematical API; no web or application dependencies."""

from .graph import GraphModel
from .scattering import scattering_matrix, validate_scattering
from .states import (
    ATOL, basis_state, density_from_state, uniform_state, validate_density,
    validate_pure, validate_state,
)
from .trajectories import ReferenceTrajectory, ReferenceVertexTrajectory, Trajectory, TrajectoryEngine
from .walk import DensityStepper, PureStateStepper, ScatteringWalk
from .vertex import InducedVertexWalk
from .edge_markov import (
    EdgeReduction, EdgeSession, EdgeConditionalState, EdgeMeanState,
    OptimizedEdgeTrajectory, CompactEdgeTrajectory, edge_eligibility,
)
from .vertex_markov import VertexReduction, OptimizedVertexTrajectory, vertex_eligibility
from .ensembles import run_ensemble, EnsembleResult, EnsembleFrame

__all__ = [
    "ATOL", "GraphModel", "ScatteringWalk", "scattering_matrix", "validate_scattering",
    "basis_state", "uniform_state", "density_from_state", "validate_pure",
    "validate_density", "validate_state", "ReferenceTrajectory", "Trajectory",
    "TrajectoryEngine", "PureStateStepper", "DensityStepper", "InducedVertexWalk",
    "EdgeReduction", "EdgeSession", "EdgeConditionalState", "EdgeMeanState",
    "OptimizedEdgeTrajectory", "CompactEdgeTrajectory", "edge_eligibility",
    "VertexReduction", "OptimizedVertexTrajectory", "ReferenceVertexTrajectory", "vertex_eligibility",
    "run_ensemble", "EnsembleResult", "EnsembleFrame",
]
