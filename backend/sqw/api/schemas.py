"""Version-one JSON contract. Complex scalars are [real, imaginary] pairs."""
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

FiniteFloat = Annotated[float, Field(strict=True, allow_inf_nan=False)]
VertexLabel = Annotated[int, Field(strict=True)]
ComplexScalar = tuple[FiniteFloat, FiniteFloat]
ComplexMatrix = list[list[ComplexScalar]]
Preset = Literal["identity", "grover", "hadamard", "dft", "random", "permutation"]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class GraphSpec(StrictModel):
    kind: Literal["path", "cycle", "complete", "star", "custom"] = "cycle"
    size: int = Field(default=6, ge=2, le=32, strict=True)
    vertices: list[Annotated[int, Field(strict=True, ge=0, le=2**31-1)]] | None = Field(default=None, max_length=32)
    edges: list[tuple[VertexLabel, VertexLabel]] | None = Field(default=None, max_length=128)
    neighbors: dict[str, list[VertexLabel]] | None = None

    @model_validator(mode='after')
    def custom_contract(self):
        supplied = (self.vertices, self.edges, self.neighbors)
        if self.kind == 'custom':
            if any(v is None for v in supplied):
                raise ValueError('Custom graphs require vertices, edges and explicit neighbor ordering.')
            if len(self.vertices) != self.size:
                raise ValueError('Custom size must match the number of vertices.')
        elif any(v is not None for v in supplied):
            raise ValueError('Preset graphs cannot include custom graph fields.')
        return self


class GraphRequest(GraphSpec):
    preset: Preset = "dft"
    seed: int = Field(default=42, ge=0, le=2**32 - 1, strict=True)


class ScatteringRequest(StrictModel):
    preset: Preset
    degree: int = Field(ge=1, le=31, strict=True)
    seed: int = Field(default=42, ge=0, le=2**32 - 1, strict=True)


class ScatteringValidationRequest(StrictModel):
    degree: int = Field(ge=1, le=31, strict=True)
    matrix: ComplexMatrix


class InitialState(StrictModel):
    kind: Literal["basis", "uniform", "pure", "mixed", "maximally_mixed"] = "basis"
    edge: tuple[VertexLabel, VertexLabel] | None = None
    vertex: VertexLabel | None = None
    vector: list[ComplexScalar] | None = None
    density: ComplexMatrix | None = None


class VertexParameters(StrictModel):
    omega: dict[str, list[ComplexScalar]] | None = None
    beta: dict[str, FiniteFloat] | None = None


class SimulationRequest(StrictModel):
    graph: GraphSpec = Field(default_factory=GraphSpec)
    preset: Preset = "dft"
    scattering: dict[str, ComplexMatrix] | None = None
    mode: Literal["unitary", "open", "trajectory", "vertex"] = "unitary"
    strategy: Literal["reference", "optimized"] = "reference"
    vertex_dynamics: Literal["trajectory", "mean"] = "trajectory"
    vertex_parameters: VertexParameters = Field(default_factory=VertexParameters)
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
    stage: str = "initial"
    state_kind: str = "conditional"
    atom_id: int | None = None
    atom_edge: tuple[int, int] | None = None
    atom_vertex: int | None = None
    state_weights: list[float] | None = None


class SimulationResponse(StrictModel):
    graph: GraphResponse
    mode: str
    frames: list[Frame]
    outcomes: list[int]
    strategy: str = "reference"
    model: str = "edge"


class EnsembleRequest(SimulationRequest):
    mode: Literal["trajectory", "vertex"] = "trajectory"
    trajectories: int = Field(default=1000, ge=1, le=100_000, strict=True)
    selected_histories: int = Field(default=3, ge=0, le=20, strict=True)
    statistics: list[Literal["states", "vertices", "edges", "exact"]] = Field(default_factory=lambda: ["states", "vertices", "edges", "exact"])


class AnalysisRequest(SimulationRequest):
    mode: Literal["open", "trajectory", "vertex"] = "trajectory"
    atom_id: int = Field(default=0, ge=0, strict=True)


class StationaryRequest(SimulationRequest):
    mode: Literal["open", "trajectory", "vertex"] = "trajectory"
    analysis_steps: int = Field(default=200, ge=0, le=5000, strict=True)
    support_atol: FiniteFloat = Field(default=1e-14, ge=0, le=1e-6)
    include_density: bool = Field(default=False, strict=True)
    stationary_class: int | None = Field(default=None, ge=0, strict=True)


class ObservableSpec(StrictModel):
    kind: Literal['label_indicator', 'outcome_indicator', 'vertex_probability',
                  'coherence_real', 'coherence_imag', 'quantum', 'label_values'] = 'label_indicator'
    index: int = Field(default=0, ge=0, strict=True)
    second: int = Field(default=1, ge=0, strict=True)
    vertex: VertexLabel | None = None
    matrix: ComplexMatrix | None = None
    values: list[FiniteFloat] | None = None


class StatisticsRequest(SimulationRequest):
    mode: Literal['open', 'trajectory', 'vertex'] = 'trajectory'
    observable: ObservableSpec = Field(default_factory=ObservableSpec)
    samples: int = Field(default=2000, ge=1, le=100_000, strict=True)
    burn_in: int = Field(default=0, ge=0, le=10_000, strict=True)
    trajectory_seed: int = Field(default=42, ge=0, le=2**32-1, strict=True)
    initialization: Literal['experiment', 'stationary_class'] = 'experiment'
    stationary_class: int = Field(default=0, ge=0, strict=True)
    confidence: FiniteFloat = Field(default=.95, gt=0, lt=1)
    support_atol: FiniteFloat = Field(default=1e-14, ge=0, le=1e-6)


class VertexPresentation(StrictModel):
    id: Annotated[int, Field(strict=True, ge=0, le=2**31-1)]
    label: str = Field(min_length=1, max_length=64, strict=True)
    position: tuple[FiniteFloat, FiniteFloat]


class ExperimentDocument(StrictModel):
    format: Literal['sqw-experiment']
    version: Annotated[int, Field(strict=True, ge=1, le=1)]
    experiment: SimulationRequest
    vertices: list[VertexPresentation] = Field(min_length=2, max_length=32)
    matrix_presets: dict[str, Preset | None]
