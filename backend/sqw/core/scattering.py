"""Unitary matrices in the explicit neighbor order of each vertex."""

from numbers import Integral

import numpy as np
from numpy.typing import ArrayLike

from .states import ATOL, ComplexArray, complex_array, validate_tolerance


def validate_scattering(matrix: ArrayLike, degree: int, *, atol: float = ATOL) -> ComplexArray:
    validate_tolerance(atol)
    if not isinstance(degree, Integral) or isinstance(degree, bool) or degree < 1:
        raise ValueError("Scattering degree must be a positive integer.")
    array = complex_array(matrix, "Scattering matrix")
    if array.shape != (degree, degree):
        raise ValueError(f"Scattering matrix must have shape ({degree}, {degree}); received {array.shape}.")
    identity = np.eye(degree)
    with np.errstate(over="ignore", invalid="ignore"):
        error = float(np.max(np.abs(array.conj().T @ array - identity)))
    if not np.isfinite(error) or error > atol:
        raise ValueError(f"Scattering matrix must be unitary; max |S†S - I| = {error:.3g} > {atol:.3g}.")
    return array


def scattering_matrix(kind: str, degree: int, rng: np.random.Generator | None = None) -> ComplexArray:
    """Generate a local unitary.

    DFT uses exp(+2 pi i j k / d) / sqrt(d), j,k=0,...,d-1.
    Random unitaries use complex Gaussian QR with corrected diagonal phases
    (Haar distribution); pass a NumPy Generator for reproducibility.
    """
    if not isinstance(degree, Integral) or isinstance(degree, bool) or degree < 1:
        raise ValueError("Scattering degree must be a positive integer.")
    if kind == "identity":
        matrix = np.eye(degree, dtype=complex)
    elif kind == "grover":
        matrix = 2 * np.ones((degree, degree), dtype=complex) / degree - np.eye(degree)
    elif kind == "hadamard":
        if degree != 2:
            raise ValueError("Hadamard scattering is defined only at vertices of degree 2.")
        matrix = np.array([[1, 1], [1, -1]], dtype=complex) / np.sqrt(2)
    elif kind in ("dft", "fourier"):
        indices = np.arange(degree)
        matrix = np.exp(2j * np.pi * np.outer(indices, indices) / degree) / np.sqrt(degree)
    elif kind == "random":
        generator = np.random.default_rng() if rng is None else rng
        if not isinstance(generator, np.random.Generator):
            raise ValueError("rng must be a NumPy Generator.")
        gaussian = generator.normal(size=(degree, degree)) + 1j * generator.normal(size=(degree, degree))
        q, r = np.linalg.qr(gaussian)
        diagonal = np.diag(r)
        phases = np.ones(degree, dtype=complex)
        nonzero = np.abs(diagonal) > 0
        phases[nonzero] = diagonal[nonzero] / np.abs(diagonal[nonzero])
        matrix = q * phases
    else:
        raise ValueError(f"Unknown scattering preset {kind!r}; use identity, grover, hadamard, dft, or random.")
    return validate_scattering(matrix, degree)
