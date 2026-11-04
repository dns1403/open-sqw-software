export type Complex = [number, number];
export type Matrix = Complex[][];
export type GraphKind = 'path' | 'cycle' | 'complete' | 'star';
export type Preset = 'identity' | 'grover' | 'hadamard' | 'dft' | 'random';
export type Mode = 'unitary' | 'open' | 'trajectory';
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
  initial: { kind: 'basis' | 'uniform'; edge: [number, number] };
  steps: number;
  seed: number;
}
