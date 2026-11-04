"""Bounded structural and phase-dependent statistical caches."""
from functools import lru_cache
from sqw.core import ClasswiseStatistics, TrajectoryStatistics
from .stationary_cache import structural_stationary_model


@lru_cache(maxsize=16)
def _classwise(chain):
    return ClasswiseStatistics(chain)


@lru_cache(maxsize=32)
def _phase_engine(base, beta):
    selected = base if beta is None else base.with_beta(dict(beta))
    return TrajectoryStatistics(selected, statistics=_classwise(base.chain))


def statistics_model(edge, vertex=None, *, support_atol=1e-14):
    base = structural_stationary_model(edge, vertex, support_atol=support_atol)
    beta = None if vertex is None else tuple((x, float(vertex.beta[x])) for x in edge.graph.vertices)
    return _phase_engine(base, beta)
