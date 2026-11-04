export type ObservableKind = 'label_indicator' | 'outcome_indicator' | 'vertex_probability' | 'coherence_real' | 'coherence_imag';
export interface PoissonResult {
  mean: number; period: number; instantaneous_variance: number; asymptotic_variance: number;
  asymptotic_std: number; degenerate: boolean; stability_warning: boolean;
  poisson_residual: number; relative_residual: number; centering_residual: number;
  stationary_residual: number; condition_number: number | null; min_scaled_pivot: number;
  variance_identity_relative_error: number; solution: number[]; stationary: number[];
}
export interface StatisticsResult {
  model: 'edge' | 'vertex'; orientation: 'row' | 'column'; start_step: number; irreducible: boolean;
  atom_labels: (number | [number, number])[];
  observable: { kind: string; values: number[] };
  analysis: {
    classes: { index: number; class_id: number; states: number[]; absorption_probability: number; reachable: boolean; poisson: PoissonResult }[];
    initial_transient_mass: number; reachable_class_indices: number[]; ensemble_limit_mean: number;
    between_class_variance: number; global_clt_available: boolean;
    global_mean: number | null; global_asymptotic_variance: number | null;
  };
  uncertainty: { standard_error: number; iid_comparison_standard_error: number; half_width: number | null; approximate: boolean; simultaneous: boolean }[];
  trajectory: {
    samples: number; burn_in: number; first_step: number; last_step: number; seed: number;
    stationary_start_requested: boolean; requested_class: number | null;
    entered_class: number | null; class_entry_step: number | null; support_escape: boolean; support_sensitive: boolean;
    empirical_mean: number; empirical_law: number[]; confidence: number; confidence_interval: [number, number] | null;
    points: { samples: number; step: number; mean: number; half_width: number | null; reference_mean: number | null }[];
  };
  support: { source: string; tolerance: number; discarded_entries: number; discarded_max_row_mass: number; matrix_change_max_row_l1: number };
}
