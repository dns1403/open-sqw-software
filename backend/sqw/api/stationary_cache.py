"""Bounded model cache, independent of initial states, horizons and beta.

Full complex coin and omega bytes + explicit graph basis are the key. No
rounded numerical hash can accidentally reuse another experiment's structure.
"""
from functools import lru_cache
import numpy as np
from sqw.core import GraphModel, ScatteringWalk, InducedVertexWalk, StationaryAnalysis


@lru_cache(maxsize=16)
def _structural_model(vertices, edges, coins, omega, support_atol):
    graph = GraphModel.from_edges(vertices, edges)
    matrices = {x: np.frombuffer(data, dtype=np.complex128).reshape(graph.degree(x), graph.degree(x))
                for x, data in zip(vertices, coins)}
    walk = ScatteringWalk(graph, matrices)
    if omega is not None:
        vectors = {x: np.frombuffer(data, dtype=np.complex128) for x, data in zip(vertices, omega)}
        walk = InducedVertexWalk(walk, vectors)  # phase-zero baseline; P is beta invariant
    return StationaryAnalysis(walk, support_atol=support_atol)


def stationary_model(edge, vertex=None, *, support_atol=1e-14):
    coins = tuple(np.asarray(edge.scattering[x], dtype=np.complex128).tobytes() for x in edge.graph.vertices)
    omega = None if vertex is None else tuple(np.asarray(vertex.omega[x], dtype=np.complex128).tobytes() for x in edge.graph.vertices)
    base = _structural_model(edge.graph.vertices, edge.graph.edges, coins, omega, support_atol)
    return base if vertex is None else base.with_beta(vertex.beta)
