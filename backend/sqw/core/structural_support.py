"""Analytical supports for exactly recognized built-in matrices, never allclose.

Recognition is deliberately conservative. Arbitrary edited matrices use the
explicit numerical-support policy in MarkovAnalysis. No state or operator is
modified by this metadata (in particular, tiny physical amplitudes survive).
"""
import numpy as np
from scipy.sparse import csr_matrix
from .scattering import scattering_matrix


def builtin_kind(matrix):
    d = len(matrix)
    for kind in ('dft', 'identity', 'grover', *(['hadamard'] if d == 2 else [])):
        if np.array_equal(matrix, scattering_matrix(kind, d)):
            return kind
    return None


def edge_support(graph, scattering):
    rows, cols = [], []
    for x in graph.vertices:
        d, s = graph.degree(x), scattering[x]
        kind = builtin_kind(s)
        if kind is None: return None
        mask = np.eye(d, dtype=bool) if kind == 'identity' else (2 / d - np.eye(d)) != 0 if kind == 'grover' else np.ones((d, d), bool)
        r, c = np.nonzero(mask)
        rows.extend(graph.outgoing_indices(x)[r]); cols.extend(graph.incoming_indices(x)[c])
    return csr_matrix((np.ones(len(rows), bool), (rows, cols)), shape=(graph.dimension, graph.dimension))


def vertex_support(graph, scattering, omega):
    """X-04: row P support for uniform omega and recognized DFT/Grover/I.

    A DFT row prepares the first neighbor plus a coherent self-completion iff
    that neighbor has degree > 1. Identity/Grover have S omega = omega.
    Neighbor order is the stored order, including any explicit basis conversion.
    """
    if any(not np.array_equal(omega[x], np.ones(graph.degree(x)) / np.sqrt(graph.degree(x))) for x in graph.vertices):
        return None
    rows, cols = [], []
    for i, x in enumerate(graph.vertices):
        kind = builtin_kind(scattering[x])
        if kind in ('dft', 'hadamard'):
            z = graph.neighbors[x][0]
            destinations = [z] + ([x] if graph.degree(z) > 1 else [])
        elif kind in ('grover', 'identity'):
            destinations = list(graph.neighbors[x])
            if any(graph.degree(z) > 1 for z in graph.neighbors[x]): destinations.append(x)
        else: return None
        rows.extend([i] * len(destinations)); cols.extend(graph.vertex_index[z] for z in destinations)
    return csr_matrix((np.ones(len(rows), bool), (rows, cols)), shape=(len(graph.vertices), len(graph.vertices)))
