export type Complex = [number, number];
export type Matrix = Complex[][];
export type GraphKind = 'path' | 'cycle' | 'complete' | 'star';
export type Preset = 'identity' | 'grover' | 'hadamard' | 'dft' | 'random';
export type Mode = 'unitary' | 'open' | 'trajectory' | 'vertex';
export type Strategy = 'reference' | 'optimized';
export interface VertexParameters { omega?: Record<string, Complex[]>; beta?: Record<string, number>; }
export interface GraphData {
  vertices: number[];
  edges: [number, number][];
  directed_edges: [number, number][];
  neighbors: Record<string, number[]>;
  scattering: Record<string, Matrix>;
  dimension: number;
}
export interface Frame {
  step: number;
  edge_probabilities: number[];
  vertex_probabilities: number[];
  purity: number;
  trace: number;
  measurement: number | null;
  measurement_probability: number | null;
  measurement_probabilities: number[] | null;
  stage?: string;
  state_kind?: 'conditional' | 'mean' | 'unitary';
  atom_id?: number | null;
  atom_edge?: [number, number] | null;
  atom_vertex?: number | null;
  state_weights?: number[] | null;
}
export interface Simulation {
  graph: GraphData;
  mode: Mode;
  frames: Frame[];
  outcomes: number[];
}
export interface SimulationRequest {
  graph: { kind: GraphKind; size: number };
  scattering: Record<string, Matrix>;
  preset: Preset;
  mode: Mode;
  initial: { kind: 'basis' | 'uniform' | 'maximally_mixed'; edge: [number, number]; vertex?: number };
  steps: number;
  seed: number;
  strategy?: Strategy;
  vertex_dynamics?: 'trajectory' | 'mean';
  vertex_parameters?: VertexParameters;
}

export interface EnsembleFrame {
  step: number;
  state_counts: number[] | null;
  outcome_counts: number[] | null;
  empirical_born_vertices: number[];
  empirical_born_edges: number[] | null;
  exact_state_weights: number[] | null;
  exact_born_vertices: number[];
  exact_born_edges: number[] | null;
  state_total_variation: number | null;
  born_vertex_total_variation: number | null;
}
export interface Ensemble {
  model: 'edge' | 'vertex'; strategy: Strategy; trajectories: number; seed: number;
  frames: EnsembleFrame[]; selected_outcomes: number[][]; selected_state_ids: (number | null)[][];
}
export interface Analysis {
  model: 'edge' | 'vertex'; orientation: 'row' | 'column'; state_step: number; stage: string;
  current_density: Matrix; after_measurement_density: Matrix | null;
  atom_id: number; atom_labels: (number | [number, number])[];
  atom_ket: Complex[]; transition_matrix: number[][]; next_atom_probabilities: number[];
  eligible: boolean; assumptions: string;
}
