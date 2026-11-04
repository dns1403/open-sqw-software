"""Independent induced vertex channel from Joye Section 6, equations 6.1-6.18."""

from collections.abc import Mapping
from math import fsum
from types import MappingProxyType

import numpy as np
from numpy.typing import ArrayLike, NDArray

from .states import (
    ATOL, ComplexArray, checked_probabilities, complex_array,
    validate_density, validate_pure, validate_steps,
)
from .walk import ScatteringWalk


class InducedVertexWalk:
    """The CPTP map Psi on vertices, not an edge-walk vertex marginal.

    ``omega[x]`` is a unit vector indexed by ``graph.neighbors[x]``.
    ``beta[x]`` is a finite real phase in radians. Omitted omega uses uniform
    local vectors; omitted beta uses zero at every vertex. Supplied mappings
    must contain exactly the graph vertices.

    The boundary operator R is n_vertices by n_directed_edges. theta[x] and
    chi[x] are full vertex vectors ordered by graph.vertices. G_x=|chi_x><x|.
    The row-stochastic markov_matrix satisfies p_next=p @ markov_matrix.
    """

    def __init__(
        self,
        edge_walk: ScatteringWalk,
        omega: Mapping[int, ArrayLike] | None = None,
        beta: Mapping[int, float] | None = None,
    ):
        if not isinstance(edge_walk, ScatteringWalk):
            raise ValueError("edge_walk must be a ScatteringWalk.")
        self.graph = edge_walk.graph
        self.dimension = len(self.graph.vertices)
        for name, mapping in (("omega", omega), ("beta", beta)):
            if mapping is not None and (
                not isinstance(mapping, Mapping) or set(mapping) != set(self.graph.vertices)
            ):
                raise ValueError(f"{name} must provide exactly one entry for every vertex.")

        vectors = {}
        phases = {}
        for x in self.graph.vertices:
            degree = self.graph.degree(x)
            value = np.ones(degree) / np.sqrt(degree) if omega is None else omega[x]
            try:
                vector = validate_pure(value, degree)
            except ValueError as exc:
                raise ValueError(f"omega at vertex {x}: {exc}") from exc
            vector.setflags(write=False)
            vectors[x] = vector
            try:
                phase = 0.0 if beta is None else float(beta[x])
            except (ValueError, TypeError, OverflowError) as exc:
                raise ValueError(f"beta at vertex {x} must be a finite real phase.") from exc
            if not np.isfinite(phase):
                raise ValueError(f"beta at vertex {x} must be a finite real phase.")
            phases[x] = phase
        self.omega = MappingProxyType(vectors)
        self.beta = MappingProxyType(phases)

        self._boundary = np.zeros((self.dimension, self.graph.dimension), dtype=complex)
        for x in self.graph.vertices:
            self._boundary[self.graph.vertex_index[x], self.graph.incoming_indices(x)] = vectors[x].conj()

        theta = {}
        chi = {}
        for x in self.graph.vertices:
            local_scattered = edge_walk.scattering[x] @ vectors[x]
            reduced = np.zeros(self.dimension, dtype=complex)
            missing_terms = []
            for i, z in enumerate(self.graph.neighbors[x]):
                reverse_index = self.graph.neighbors[z].index(x)
                reduced[self.graph.vertex_index[z]] = vectors[z][reverse_index].conjugate() * local_scattered[i]
                # V-01 / T34: for normalized boundary vectors and S omega,
                # 1-||theta||² = sum_z |v_z|² sum_{u != x} |omega_u(z)|².
                # Sum nonnegative complementary port masses instead of
                # subtracting two near-unit numbers before a square root.
                # This preserves genuine tiny masses; no threshold is used.
                complement = fsum(float(abs(value) ** 2) for j, value in enumerate(vectors[z]) if j != reverse_index)
                missing_terms.append(float(abs(local_scattered[i]) ** 2) * complement)
            norm_squared = float(np.vdot(reduced, reduced).real)
            if norm_squared > 1 + ATOL:
                raise ArithmeticError("The norm of theta exceeds one beyond numerical tolerance.")
            completed = reduced.copy()
            completed[self.graph.vertex_index[x]] = np.exp(1j * phases[x]) * np.sqrt(fsum(missing_terms))
            validate_pure(completed, self.dimension)
            reduced.setflags(write=False)
            completed.setflags(write=False)
            theta[x] = reduced
            chi[x] = completed
        self.theta = MappingProxyType(theta)
        self.chi = MappingProxyType(chi)

    @property
    def boundary_operator(self) -> ComplexArray:
        """Detached R from equation (6.1)."""
        return self._boundary.copy()

    @property
    def markov_matrix(self) -> NDArray[np.float64]:
        """P[x,y]=|<y|chi(x)>|², with rows and columns in vertex order."""
        return np.array([np.abs(self.chi[x]) ** 2 for x in self.graph.vertices])

    def kraus_operators(self) -> tuple[ComplexArray, ...]:
        matrices = []
        for i, x in enumerate(self.graph.vertices):
            matrix = np.zeros((self.dimension, self.dimension), dtype=complex)
            matrix[:, i] = self.chi[x]
            matrices.append(matrix)
        return tuple(matrices)

    def apply_channel(self, operator: ArrayLike) -> ComplexArray:
        """Exact linear Kraus sum using G_x A G_x†=A_xx |chi_x><chi_x|."""
        array = complex_array(operator, "Vertex operator")
        if array.shape != (self.dimension, self.dimension):
            raise ValueError(f"Vertex operator must have shape ({self.dimension}, {self.dimension}).")
        result = np.zeros_like(array)
        for i, x in enumerate(self.graph.vertices):
            result += array[i, i] * np.outer(self.chi[x], self.chi[x].conj())
        return result

    def step_density(self, state: ArrayLike) -> ComplexArray:
        return self.apply_channel(validate_density(state, self.dimension))

    def evolve_density(self, initial: ArrayLike, steps: int) -> tuple[ComplexArray, ...]:
        count = validate_steps(steps)
        state = validate_density(initial, self.dimension)
        states = [state]
        for _ in range(count):
            state = self.apply_channel(state)
            states.append(state)
        return tuple(states)

    def vertex_probabilities(self, state: ArrayLike) -> NDArray[np.float64]:
        array = validate_density(state, self.dimension)
        return checked_probabilities(np.diag(array).real)
