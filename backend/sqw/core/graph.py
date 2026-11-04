"""Finite simple graphs with a deterministic directed-edge Hilbert basis."""

from collections.abc import Iterable, Mapping
from numbers import Integral
from types import MappingProxyType

import networkx as nx
import numpy as np


class GraphModel:
    """A connected undirected graph with integer vertex labels.

    ``directed_edges[i] == (x, y)`` means ``|xy>`` points from y to x.
    Vertices and each neighbor list are sorted numerically. The edge basis is
    ordered first by target x, then source y. User insertion order has no effect.
    Construct using ``from_edges``, ``from_networkx``, or ``preset``.
    """

    def __init__(self, graph: nx.Graph):
        if not isinstance(graph, nx.Graph) or graph.is_directed() or graph.is_multigraph():
            raise ValueError("Expected a simple undirected NetworkX graph.")
        if any(not isinstance(v, Integral) or isinstance(v, bool) for v in graph.nodes):
            raise ValueError("Vertex labels must be integers (not booleans).")
        if len(graph) < 2:
            raise ValueError("A scattering graph needs at least two vertices.")
        if nx.number_of_selfloops(graph):
            raise ValueError("Self-loops are not allowed in a simple scattering graph.")
        if not nx.is_connected(graph):
            raise ValueError("The graph must be connected; isolated vertices are not allowed.")

        self._vertices = tuple(sorted(int(v) for v in graph.nodes))
        self._neighbors = MappingProxyType({
            x: tuple(sorted(int(y) for y in graph.neighbors(x))) for x in self._vertices
        })
        self._edges = tuple((x, y) for x in self._vertices for y in self._neighbors[x] if x < y)
        self._directed_edges = tuple((x, y) for x in self._vertices for y in self._neighbors[x])
        self._edge_index = MappingProxyType({edge: i for i, edge in enumerate(self._directed_edges)})
        self._vertex_index = MappingProxyType({x: i for i, x in enumerate(self._vertices)})

    @classmethod
    def from_networkx(cls, graph: nx.Graph) -> "GraphModel":
        return cls(graph)

    @classmethod
    def from_edges(cls, nodes: Iterable[int], edges: Iterable[tuple[int, int]]) -> "GraphModel":
        node_list = list(nodes)
        if any(not isinstance(v, Integral) or isinstance(v, bool) for v in node_list):
            raise ValueError("Vertex labels must be integers (not booleans).")
        if len(set(node_list)) != len(node_list):
            raise ValueError("Vertex labels must be unique.")
        graph = nx.Graph()
        graph.add_nodes_from(node_list)
        seen: set[tuple[int, int]] = set()
        for edge in edges:
            try:
                u, v = edge
            except (TypeError, ValueError) as exc:
                raise ValueError("Each edge must contain exactly two integer vertex labels.") from exc
            if any(not isinstance(w, Integral) or isinstance(w, bool) for w in (u, v)):
                raise ValueError("Edge endpoints must be integer vertex labels.")
            if u not in graph or v not in graph:
                raise ValueError(f"Edge ({u}, {v}) references an unknown vertex.")
            if u == v:
                raise ValueError("Self-loops are not allowed in a simple scattering graph.")
            canonical = tuple(sorted((int(u), int(v))))
            if canonical in seen:
                raise ValueError(f"Duplicate undirected edge {canonical} is not allowed.")
            seen.add(canonical)
            graph.add_edge(u, v)
        return cls(graph)

    @classmethod
    def preset(cls, kind: str, size: int) -> "GraphModel":
        """Create a graph on ``size`` vertices, labeled 0 through size-1.

        For stars, size includes the central vertex 0; cycles need size >= 3.
        """
        if not isinstance(size, Integral) or isinstance(size, bool) or size < 2:
            raise ValueError("Graph size must be an integer of at least 2.")
        if kind == "path":
            graph = nx.path_graph(size)
        elif kind == "cycle":
            if size < 3:
                raise ValueError("A simple cycle requires at least 3 vertices.")
            graph = nx.cycle_graph(size)
        elif kind == "complete":
            graph = nx.complete_graph(size)
        elif kind == "star":
            graph = nx.star_graph(size - 1)
        else:
            raise ValueError(f"Unknown graph preset {kind!r}; use path, cycle, complete, or star.")
        return cls(graph)

    @property
    def vertices(self) -> tuple[int, ...]:
        return self._vertices

    @property
    def neighbors(self) -> Mapping[int, tuple[int, ...]]:
        return self._neighbors

    @property
    def directed_edges(self) -> tuple[tuple[int, int], ...]:
        return self._directed_edges

    @property
    def undirected_edges(self) -> tuple[tuple[int, int], ...]:
        return self._edges

    @property
    def edges(self) -> tuple[tuple[int, int], ...]:
        return self._edges

    @property
    def edge_index(self) -> Mapping[tuple[int, int], int]:
        return self._edge_index

    @property
    def vertex_index(self) -> Mapping[int, int]:
        return self._vertex_index

    @property
    def dimension(self) -> int:
        return len(self._directed_edges)

    def degree(self, vertex: int) -> int:
        return len(self._neighbors[vertex])

    def incoming_indices(self, vertex: int) -> np.ndarray:
        return np.array([self._edge_index[(vertex, y)] for y in self._neighbors[vertex]], dtype=int)

    def outgoing_indices(self, vertex: int) -> np.ndarray:
        return np.array([self._edge_index[(y, vertex)] for y in self._neighbors[vertex]], dtype=int)

    def to_networkx(self) -> nx.Graph:
        """Return a detached graph; edits cannot invalidate this model's basis."""
        graph = nx.Graph()
        graph.add_nodes_from(self._vertices)
        graph.add_edges_from(self._edges)
        return graph
