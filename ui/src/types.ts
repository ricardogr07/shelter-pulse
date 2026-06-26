export interface AllocationIn {
  foster_support: number;
  clinic_hours: number;
  temporary_isolation: number;
  adoption_events: number;
}

export interface EvaluationResult {
  foster_support: number;
  clinic_hours: number;
  temporary_isolation: number;
  adoption_events: number;
  mean_overflow_cat_days: number;
  std_overflow_cat_days: number;
  mean_total_cost: number;
  is_feasible: boolean;
}
