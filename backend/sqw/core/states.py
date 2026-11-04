"""State validation and constructors, independent of any evolution engine."""

from numbers import Integral

import numpy as np
from numpy.typing import ArrayLike, NDArray

from .graph import GraphModel

ATOL = 1e-10
ComplexArray = NDArray[np.complex128]


def validate_tolerance(atol: float) -> None:
    if not np.isscalar(atol) or not np.isfinite(atol) or atol < 0:
        raise ValueError("Numerical tolerance must be finite and nonnegative.")


def complex_array(value: ArrayLike, name: str = "Array") -> ComplexArray:
    try:
        array = np.array(value, dtype=np.complex128, copy=True)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{name} must contain complex numbers in a rectangular array.") from exc
    if not np.all(np.isfinite(array)):
        raise ValueError(f"{name} must contain only finite numbers.")
    return array


def validate_pure(state: ArrayLike, dimension: int | None = None, *, atol: float = ATOL) -> ComplexArray:
    """Return a copy of a normalized vector; never normalize invalid input."""
    validate_tolerance(atol)
    array = complex_array(state, "State vector")
    if array.ndim != 1 or not array.size or (dimension is not None and array.shape != (dimension,)):
        raise ValueError(f"State vector must have shape ({dimension if dimension is not None else 'N'},).")
    norm_squared = float(np.vdot(array, array).real)
    if not np.isclose(norm_squared, 1.0, rtol=0, atol=atol):
        raise ValueError(f"State vector must be normalized; squared norm is {norm_squared:.12g}.")
    return array


def validate_density(state: ArrayLike, dimension: int | None = None, *, atol: float = ATOL) -> ComplexArray:
    """Return a copy after checking shape, trace, Hermiticity and positivity."""
    validate_tolerance(atol)
    array = complex_array(state, "Density matrix")
    if array.ndim != 2 or not array.size or array.shape[0] != array.shape[1]:
        raise ValueError("Density matrix must be a nonempty square matrix.")
    if dimension is not None and array.shape != (dimension, dimension):
        raise ValueError(f"Density matrix must have shape ({dimension}, {dimension}).")
    if not np.allclose(array, array.conj().T, rtol=0, atol=atol):
        raise ValueError("Density matrix must be Hermitian.")
    trace = np.trace(array)
    if not np.isclose(trace, 1.0, rtol=0, atol=atol):
        raise ValueError(f"Density matrix must have trace 1; trace is {trace}.")
    minimum = float(np.linalg.eigvalsh(array)[0])
    if minimum < -atol:
        raise ValueError(f"Density matrix must be positive semidefinite; minimum eigenvalue is {minimum:.12g}.")
    return array


def validate_state(state: ArrayLike, dimension: int) -> ComplexArray:
    array = complex_array(state, "Quantum state")
    if array.ndim == 1:
        return validate_pure(array, dimension)
    return validate_density(array, dimension)


def density_from_state(state: ArrayLike) -> ComplexArray:
    vector = validate_pure(state)
    return np.outer(vector, vector.conj())


def basis_state(graph: GraphModel, edge: tuple[int, int]) -> ComplexArray:
    """The basis vector |xy> for edge=(x,y), pointing from y to x."""
    try:
        pair = tuple(edge)
        if len(pair) != 2 or any(not isinstance(v, Integral) or isinstance(v, bool) for v in pair):
            raise ValueError("Directed edge endpoints must be integer labels (not booleans).")
        index = graph.edge_index[pair]
    except (KeyError, TypeError) as exc:
        raise ValueError(f"{edge!r} is not a directed edge (target, source) of this graph.") from exc
    state = np.zeros(graph.dimension, dtype=np.complex128)
    state[index] = 1.0
    return state


def uniform_state(graph: GraphModel) -> ComplexArray:
    """Equal coherent amplitudes on all directed edges (not a mixed state)."""
    return np.ones(graph.dimension, dtype=np.complex128) / np.sqrt(graph.dimension)


def validate_steps(steps: int) -> int:
    if not isinstance(steps, Integral) or isinstance(steps, bool) or steps < 0:
        raise ValueError("Number of steps must be a nonnegative integer.")
    return int(steps)


def checked_probabilities(values: ArrayLike, *, atol: float = ATOL) -> NDArray[np.float64]:
    """Validate Born probabilities and remove only tolerated roundoff.

    The final division removes floating-point drift for ``Generator.choice``.
    It does not normalize arbitrary weights or repair invalid quantum states.
    """
    validate_tolerance(atol)
    array = np.asarray(values, dtype=float)
    if array.ndim != 1 or not array.size or not np.all(np.isfinite(array)):
        raise ValueError("Probabilities must be a nonempty finite vector.")
    total = float(array.sum())
    if np.any(array < -atol) or not np.isclose(total, 1, rtol=0, atol=atol):
        raise ValueError("Born probabilities must be nonnegative and sum to 1 within tolerance.")
    array = np.maximum(array, 0.0)
    return array / array.sum()
