import type { StationaryResult } from '../types';
import type { StatisticsResult, PoissonResult } from '../statisticsTypes';

export const stationaryFixture: StationaryResult = { model: 'vertex', orientation: 'row', start_step: 1, analysis_steps: 2,
  atom_labels: [0,1,2,3], membership: [0,0,1,2], closed_class_ids: [0,1], transient_states: [3],
  classes: [
    { id: 0, states: [0,1], closed: true, period: 2, cyclic_subclasses: [[0],[1]], stationary: [.5,.5], residual: 0, raw_residual: 0 },
    { id: 1, states: [2], closed: true, period: 1, cyclic_subclasses: [[2]], stationary: [1], residual: 0, raw_residual: 0 },
    { id: 2, states: [3], closed: false, period: null, cyclic_subclasses: [], stationary: null, residual: null, raw_residual: null }],
  stationary_family: [[.5,.5,0,0],[0,0,1,0]], absorption: [[1,0],[1,0],[0,1],[.75,.25]],
  initial_law: [0,0,0,1], class_weights: [.75,.25], stationary_mixture: [.375,.375,.25,0],
  irreducible: false, unique_stationary: false, bistochastic: false, ordinary_for_all_initials: false,
  ordinary_guaranteed: false, reachable_periods: [2,1],
  support: { source: 'numerical', policy: 'numerical_threshold', tolerance: 1e-14, discarded_entries: 0,
    discarded_max_probability: 0, discarded_max_row_mass: 0, matrix_change_max_row_l1: 0 },
  diagnostics: { row_residual: 0, column_residual: 1, absorption_residual: 0, absorption_raw_residual: 0 },
  transitions: [{ source: 0, target: 1, probability: 1, analysis_probability: 1 }],
  transition_matrix: [[0,1,0,0],[1,0,0,0],[0,0,1,0],[.75,0,.25,0]],
  frames: [
    { step: 1, probabilities: [0,0,0,1], cesaro: [0,0,0,1], total_variation: 1, cesaro_total_variation: 1 },
    { step: 2, probabilities: [.75,0,.25,0], cesaro: [.375,0,.125,.5], total_variation: .375, cesaro_total_variation: .5 },
    { step: 3, probabilities: [0,.75,.25,0], cesaro: [.25,.25,1/6,1/3], total_variation: .375, cesaro_total_variation: 1/3 }],
  quantum: null };
const poisson: PoissonResult = {mean:.5,period:1,instantaneous_variance:.25,asymptotic_variance:.5,asymptotic_std:Math.sqrt(.5),degenerate:false,stability_warning:false,poisson_residual:0,relative_residual:0,centering_residual:0,stationary_residual:0,condition_number:1.5,min_scaled_pivot:1,variance_identity_relative_error:0,solution:[.75,-.75],stationary:[.5,.5]};
export const statisticsFixture: StatisticsResult = {model:'vertex',orientation:'row',start_step:1,irreducible:false,atom_labels:[0,1,2],observable:{kind:'label_indicator',values:[1,0,0]},
  analysis:{classes:[{index:0,class_id:0,states:[0,1],absorption_probability:.75,reachable:true,poisson},{index:1,class_id:1,states:[2],absorption_probability:.25,reachable:true,poisson:{...poisson,mean:0,asymptotic_variance:0,degenerate:true}}],initial_transient_mass:0,reachable_class_indices:[0,1],ensemble_limit_mean:.375,between_class_variance:.046875,global_clt_available:false,global_mean:null,global_asymptotic_variance:null},
  uncertainty:[{standard_error:.5,iid_comparison_standard_error:.35,half_width:.98,approximate:true,simultaneous:false},{standard_error:0,iid_comparison_standard_error:0,half_width:null,approximate:true,simultaneous:false}],
  trajectory:{samples:2,burn_in:0,first_step:1,last_step:2,seed:42,stationary_start_requested:false,requested_class:null,entered_class:0,class_entry_step:1,support_escape:false,support_sensitive:false,empirical_mean:.5,empirical_law:[.5,.5,0],confidence:.95,confidence_interval:[-.48,1.48],points:[{samples:1,step:1,mean:1,half_width:1.38,reference_mean:.5},{samples:2,step:2,mean:.5,half_width:.98,reference_mean:.5}]},
  support:{source:'analytic_builtin',tolerance:1e-14,discarded_entries:0,discarded_max_row_mass:0,matrix_change_max_row_l1:0}};
