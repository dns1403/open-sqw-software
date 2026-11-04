"""Version-one JSON contract. Complex scalars are [real, imaginary] pairs."""
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

FiniteFloat = Annotated[float, Field(strict=True, allow_inf_nan=False)]
VertexLabel = Annotated[int, Field(strict=True)]
ComplexScalar = tuple[FiniteFloat, FiniteFloat]
ComplexMatrix = list[list[ComplexScalar]]
Preset = Literal["identity", "grover", "hadamard", "dft", "random"]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class GraphSpec(StrictModel):
    kind: Literal["path", "cycle", "complete", "star"] = "cycle"
    size: int = Field(default=6, ge=2, le=32, strict=True)


class GraphRequest(GraphSpec):
    preset: Preset = "dft"
    seed: int = Field(default=42, ge=0, le=2**32 - 1, strict=True)


class ScatteringRequest(StrictModel):
    preset: Preset
    degree: int = Field(ge=1, le=31, strict=True)
    seed: int = Field(default=42, ge=0, le=2**32 - 1, strict=True)


class InitialState(StrictModel):
    kind: Literal["basis", "uniform"] = "basis"
    edge: tuple[VertexLabel, VertexLabel] | None = None


class SimulationRequest(StrictModel):
    graph: GraphSpec = Field(default_factory=GraphSpec)
    preset: Preset = "dft"
    scattering: dict[str, ComplexMatrix] | None = None
    mode: Literal["unitary", "open", "trajectory"] = "unitary"
    initial: InitialState = Field(default_factory=InitialState)
    steps: int = Field(default=20, ge=0, le=200, strict=True)
    seed: int = Field(default=42, ge=0, le=2**32 - 1, strict=True)


class GraphResponse(StrictModel):
    vertices: list[int]
    edges: list[tuple[int, int]]
    directed_edges: list[tuple[int, int]]
    neighbors: dict[str, list[int]]
    scattering: dict[str, ComplexMatrix]
    dimension: int


class Frame(StrictModel):
    step: int
    edge_probabilities: list[float]
    vertex_probabilities: list[float]
    purity: float
    trace: float
    measurement: int | None = None
    measurement_probability: float | None = None
    measurement_probabilities: list[float] | None = None


class SimulationResponse(StrictModel):
    graph: GraphResponse
    mode: str
    frames: list[Frame]
    outcomes: list[int]
