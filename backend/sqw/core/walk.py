"""Unitary and open edge evolution, following Joye (2.5) and (4.12)."""

from collections.abc import Mapping
from types import MappingProxyType
from typing import Protocol

import numpy as np
from numpy.typing import ArrayLike, NDArray
from scipy.sparse import csr_matrix

from .graph import GraphModel
from .scattering import validate_scattering
from .states import (
    ComplexArray, checked_probabilities, complex_array, validate_density,
    validate_pure, validate_state, validate_steps,
)


class PureStateStepper(Protocol):
    """Extension seam for sparse/local/alternative pure-state engines."""

    def step_pure(self, state: ArrayLike) -> ComplexArray: ...


class DensityStepper(Protocol):
    """Extension seam for direct or independently validated reduced channels."""

    def step_density(self, state: ArrayLike) -> ComplexArray: ...


class ScatteringWalk:
    """Validated local matrices, sparse unitary U, and a direct open channel.

    ``step_pure`` applies U. ``step_density`` applies the *open* channel
    Phi(rho)=sum_x K_x rho K_x†, not unitary conjugation. The optional
    ``step_unitary_density`` method explicitly provides the latter.
    """

    def __init__(self, graph: GraphModel, scattering: Mapping[int, ArrayLike]):
        if not isinstance(graph, GraphModel):
            raise ValueError("graph must be a GraphModel.")
        if not isinstance(scattering, Mapping) or set(scattering) != set(graph.vertices):
            raise ValueError("Provide exactly one scattering matrix for every graph vertex.")
        self.graph = graph
        matrices = {}
        for x in graph.vertices:
            try:
                matrix = validate_scattering(scattering[x], graph.degree(x))
            except ValueError as exc:
                raise ValueError(f"Vertex {x}: {exc}") from exc
            matrix.setflags(write=False)
            matrices[x] = matrix
        self.scattering = MappingProxyType(matrices)
        self._incoming = {x: graph.incoming_indices(x) for x in graph.vertices}
        self._outgoing = {x: graph.outgoing_indices(x) for x in graph.vertices}
        rows: list[int] = []
        columns: list[int] = []
        values: list[complex] = []
        for x in graph.vertices:
            for row, z in enumerate(graph.neighbors[x]):
                for column, y in enumerate(graph.neighbors[x]):
                    rows.append(graph.edge_index[(z, x)])
                    columns.append(graph.edge_index[(x, y)])
                    values.append(matrices[x][row, column])
        self._operator = csr_matrix((values, (rows, columns)), shape=(graph.dimension, graph.dimension))
        self._operator.eliminate_zeros()

    @property
    def operator(self) -> csr_matrix:
        """Detached CSR representation of U; modifying it cannot alter the walk."""
        return self._operator.copy()

    def incoming_projector(self, vertex: int) -> ComplexArray:
        if vertex not in self.graph.neighbors:
            raise ValueError(f"Unknown vertex {vertex}.")
        diagonal = np.zeros(self.graph.dimension, dtype=complex)
        diagonal[self._incoming[vertex]] = 1
        return np.diag(diagonal)

    def outgoing_projector(self, vertex: int) -> ComplexArray:
        if vertex not in self.graph.neighbors:
            raise ValueError(f"Unknown vertex {vertex}.")
        diagonal = np.zeros(self.graph.dimension, dtype=complex)
        diagonal[self._outgoing[vertex]] = 1
        return np.diag(diagonal)

    def kraus_operators(self) -> tuple[ComplexArray, ...]:
        """Dense diagnostics K_x=U P_x^I, ordered by graph.vertices.

        Evolution itself does not allocate these full matrices.
        """
        return tuple(self._operator @ self.incoming_projector(x) for x in self.graph.vertices)

    def step_pure(self, state: ArrayLike) -> ComplexArray:
        vector = validate_pure(state, self.graph.dimension)
        return np.asarray(self._operator @ vector)

    def apply_channel(self, operator: ArrayLike) -> ComplexArray:
        """Linear action Phi(A), allowing any finite square operator A.

        Uses each incoming block A[I_x,I_x], then S(x) A[I_x,I_x] S(x)†
        in outgoing block O_x. This is an exact evaluation of the Kraus sum,
        not a Markov or diagonal-state approximation.
        """
        array = complex_array(operator, "Operator")
        dimension = self.graph.dimension
        if array.shape != (dimension, dimension):
            raise ValueError(f"Operator must have shape ({dimension}, {dimension}).")
        result = np.zeros_like(array)
        for x in self.graph.vertices:
            indices = self._incoming[x]
            matrix = self.scattering[x]
            result[np.ix_(self._outgoing[x], self._outgoing[x])] = matrix @ array[np.ix_(indices, indices)] @ matrix.conj().T
        return result

    def step_density(self, state: ArrayLike) -> ComplexArray:
        return self.apply_channel(validate_density(state, self.graph.dimension))

    def step_unitary_density(self, state: ArrayLike) -> ComplexArray:
        array = validate_density(state, self.graph.dimension)
        left = self._operator @ array
        return np.asarray((self._operator @ left.conj().T).conj().T)

    def evolve_pure(self, initial: ArrayLike, steps: int) -> tuple[ComplexArray, ...]:
        count = validate_steps(steps)
        state = validate_pure(initial, self.graph.dimension)
        states = [state]
        for _ in range(count):
            state = np.asarray(self._operator @ state)
            states.append(state)
        return tuple(states)

    def evolve_density(self, initial: ArrayLike, steps: int) -> tuple[ComplexArray, ...]:
        count = validate_steps(steps)
        state = validate_density(initial, self.graph.dimension)
        states = [state]
        for _ in range(count):
            state = self.apply_channel(state)
            states.append(state)
        return tuple(states)

    def edge_probabilities(self, state: ArrayLike) -> NDArray[np.float64]:
        array = validate_state(state, self.graph.dimension)
        values = np.abs(array) ** 2 if array.ndim == 1 else np.diag(array).real
        return checked_probabilities(values)

    def vertex_probabilities(self, state: ArrayLike) -> NDArray[np.float64]:
        """Incoming vertex marginal, ordered by graph.vertices, not a vertex walk."""
        edges = self.edge_probabilities(state)
        return np.array([edges[self._incoming[x]].sum() for x in self.graph.vertices])
