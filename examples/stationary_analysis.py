"""Reproduce finite stationary examples and independent Kraus comparisons.

Run from the repository root after installing the package in editable mode.
Numbers are numerical evidence, not proofs or uniform convergence bounds.
"""
import json
import numpy as np
from sqw.core import GraphModel, ScatteringWalk, InducedVertexWalk, StationaryAnalysis, scattering_matrix


def edge_walk(kind, size, preset):
    graph = GraphModel.preset(kind, size)
    return ScatteringWalk(graph, {x: scattering_matrix(preset if graph.degree(x) > 1 else 'identity', graph.degree(x))
                                  for x in graph.vertices})


def x04():
    edge = edge_walk('path', 5, 'dft')
    coins = dict(edge.scattering)
    permutation = np.array([[0, 1], [1, 0]])
    # Requested ports at vertex 3 are [4,2], stored ports are [2,4].
    coins[3] = permutation @ coins[3] @ permutation.T
    return InducedVertexWalk(ScatteringWalk(edge.graph, coins))


def compare(name, walk, initial, steps=120):
    analysis = StationaryAnalysis(walk)
    rho = np.outer(initial, initial.conj()) if initial.ndim == 1 else initial.copy()
    for _ in range(analysis.start_step):
        rho = walk.apply_channel(rho)
    error = 0.
    for frame in analysis.evolve(initial, steps):
        error = max(error, float(np.max(abs(analysis.model.mean_density(frame.probabilities) - rho))))
        rho = walk.apply_channel(rho)
    stationary = analysis.stationary_density(initial)
    return {'case': name, 'closed_classes': [c.states for c in analysis.chain.closed_classes],
        'periods': [c.period for c in analysis.chain.closed_classes],
        'transient': analysis.chain.transient_states,
        'class_weights': analysis.mixture(initial).class_weights.tolist(),
        'stationary_mixture': analysis.mixture(initial).stationary.tolist(),
        'support_source': analysis.support_source,
        'max_mean_Kraus_error': error,
        'stationary_channel_residual': float(np.max(abs(walk.apply_channel(stationary)-stationary))),
        'final_time': frame.step, 'ordinary_TV': frame.total_variation, 'Cesaro_TV': frame.cesaro_total_variation}


def main():
    rows = []
    for preset in ('identity', 'hadamard', 'grover'):
        walk = edge_walk('path', 3, preset)
        rows.append(compare('edge_path3_' + preset, walk, np.eye(4, dtype=complex)[0]))
    walk = edge_walk('cycle', 3, 'dft')
    rows.append(compare('edge_triangle_dft', walk, np.eye(6, dtype=complex)[0]))
    rows.append(compare('vertex_X04', x04(), np.eye(5, dtype=complex)[2]))
    vertex = InducedVertexWalk(walk, {x: np.array([.6, .8j]) for x in walk.graph.vertices}, {0:.3,1:-.7,2:1.1})
    rows.append(compare('vertex_complex_omega_beta', vertex, np.eye(3, dtype=complex)[0]))
    print(json.dumps(rows, indent=2))


if __name__ == '__main__':
    main()
