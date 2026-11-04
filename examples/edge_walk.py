"""Reproducible notebook-friendly example. Run: python examples/edge_walk.py."""
import numpy as np
from sqw.core import GraphModel, ReferenceTrajectory, ScatteringWalk, density_from_state, scattering_matrix, uniform_state


def main():
    graph = GraphModel.preset("cycle", 3)
    walk = ScatteringWalk(graph, {x: scattering_matrix("dft", graph.degree(x)) for x in graph.vertices})
    initial = uniform_state(graph)
    closed = walk.evolve_pure(initial, 6)
    opened = walk.evolve_density(density_from_state(initial), 6)
    trajectory = ReferenceTrajectory(walk, seed=2026).run(initial, 6)
    print("Basis (target, source):", graph.directed_edges)
    print("t  unitary vertex probabilities    open vertex probabilities  open purity")
    for t, (psi, rho) in enumerate(zip(closed, opened)):
        print(t, np.round(walk.vertex_probabilities(psi), 4), np.round(walk.vertex_probabilities(rho), 4), round(float(np.vdot(rho, rho).real), 6))
    print("Measurements X_1,...,X_6:", trajectory.outcomes)
    print("Selected conditional probabilities:", np.round(trajectory.selected_probabilities, 4))


if __name__ == "__main__":
    main()
