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
  // optional - present once ci95 backlog item lands
  ci95_overflow_low?: number;
  ci95_overflow_high?: number;
  ci95_cost_low?: number;
  ci95_cost_high?: number;
}

export interface CustomScenario {
  name: string;
  duration_days: number;
  housing_capacity: number;
  isolation_slots: number;
  vet_tech_fte: number;
  intervention_budget: number;
  mean_intake_per_day: number;
  kitten_fraction: number;
  base_adoption_rate: number;
}
