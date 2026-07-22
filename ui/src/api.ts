export const apiBase = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const API = apiBase;

import type { AllocationIn, EvaluationResult } from "./types";
import sweepRaw from "./data/whisker-haven-sweep.json";

// --- Static showcase mode -------------------------------------------------
// When NEXT_PUBLIC_STATIC_MODE=1 the app ships with no backend (free static
// host). The /demo wizard replays a recorded Whisker Haven sweep from
// data/whisker-haven-sweep.json; the custom builder endpoints refuse with a
// friendly message so the existing error UI tells visitors to run it locally.
export const STATIC_MODE = process.env.NEXT_PUBLIC_STATIC_MODE === "1";
export const STATIC_MSG =
  "Live compute is paused: this is a free static showcase. Clone the repo and run docker-compose up for live simulation and custom scenarios.";

type RawRow = {
  allocation: AllocationIn;
  mean_overflow_cat_days: number;
  std_overflow_cat_days: number;
  mean_total_cost: number;
  is_feasible: boolean;
  source: string;
  ci95_overflow_low?: number;
  ci95_overflow_high?: number;
  ci95_cost_low?: number;
  ci95_cost_high?: number;
};

const CANNED: EvaluationResult[] = (sweepRaw as RawRow[]).map((r) => ({
  ...r.allocation,
  mean_overflow_cat_days: r.mean_overflow_cat_days,
  std_overflow_cat_days: r.std_overflow_cat_days,
  mean_total_cost: r.mean_total_cost,
  is_feasible: r.is_feasible,
  source: r.source,
  ci95_overflow_low: r.ci95_overflow_low,
  ci95_overflow_high: r.ci95_overflow_high,
  ci95_cost_low: r.ci95_cost_low,
  ci95_cost_high: r.ci95_cost_high,
}));
// winner-first: DemoClient reads sweepResults[0] as the winner
const CANNED_SORTED = [...CANNED].sort(
  (a, b) => a.mean_overflow_cat_days - b.mean_overflow_cat_days
);

function delay<T>(v: T, ms = 350): Promise<T> {
  return new Promise((res) => setTimeout(() => res(v), ms));
}
function allocEq(a: AllocationIn, b: AllocationIn): boolean {
  const e = 1e-6;
  return (
    Math.abs(a.foster_support - b.foster_support) < e &&
    Math.abs(a.clinic_hours - b.clinic_hours) < e &&
    Math.abs(a.temporary_isolation - b.temporary_isolation) < e &&
    Math.abs(a.adoption_events - b.adoption_events) < e
  );
}
function cannedMatch(a: AllocationIn): EvaluationResult {
  return CANNED.find((r) => allocEq(r, a)) ?? CANNED_SORTED[0];
}

export async function simulate(allocation: AllocationIn, reps = 32): Promise<EvaluationResult> {
  if (STATIC_MODE) return delay(cannedMatch(allocation));
  const r = await fetch(`${API}/simulate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ allocation, n_replications: reps }),
  });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function optimize(nCandidates = 20, reps = 32, useBo = true): Promise<EvaluationResult[]> {
  if (STATIC_MODE) return delay(CANNED_SORTED);
  const r = await fetch(`${API}/optimize`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ n_candidates: nCandidates, n_replications: reps, use_bo: useBo }),
  });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function getBaselines(): Promise<Record<string, AllocationIn>> {
  if (STATIC_MODE) {
    const map: Record<string, AllocationIn> = {};
    for (const row of sweepRaw as RawRow[]) {
      if (row.source.startsWith("baseline:")) {
        map[row.source.replace("baseline:", "")] = row.allocation;
      }
    }
    return delay(map);
  }
  const r = await fetch(`${API}/baselines`);
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export function exportUrl(): string {
  return `${API}/export`;
}

// Stubs comment removed - these are real now
export interface SensitivityResult { parameter: string; low_overflow: number; base_overflow: number; high_overflow: number; }
export interface DailySnapshot { day: number; housing_used: number; overflow: number; }
export interface CustomScenarioParams { name: string; duration_days: number; housing_capacity: number; isolation_slots: number; vet_tech_fte: number; intervention_budget: number; mean_intake_per_day: number; kitten_fraction: number; base_adoption_rate: number; }

export async function simulateCustom(s: CustomScenarioParams): Promise<EvaluationResult> {
  if (STATIC_MODE) throw new Error(STATIC_MSG);
  const r = await fetch(`${API}/simulate/builder`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(s) });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function simulateWhatIf(s: CustomScenarioParams, allocation: { foster_support: number; clinic_hours: number; temporary_isolation: number; adoption_events: number }): Promise<EvaluationResult> {
  if (STATIC_MODE) throw new Error(STATIC_MSG);
  const r = await fetch(`${API}/simulate/builder`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ ...s, allocation, n_replications: 4 }) });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function optimizeCustom(s: CustomScenarioParams, nCandidates = 20, reps = 32, consent?: { consent_storage: boolean; is_test_data: boolean }): Promise<EvaluationResult[]> {
  if (STATIC_MODE) throw new Error(STATIC_MSG);
  const r = await fetch(`${API}/optimize/builder`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ ...s, n_candidates: nCandidates, n_replications: reps, ...(consent || {}) }) });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export interface PreviousRun {
  job_id: string;
  created_at: string;
  scenario_name: string;
  duration_days: number;
  housing_capacity: number;
  isolation_slots: number;
  intervention_budget: number;
  mean_intake_per_day: number;
  winner_foster_support: number;
  winner_clinic_hours: number;
  winner_temporary_isolation: number;
  winner_adoption_events: number;
  winner_mean_overflow: number;
  winner_mean_cost: number;
  winner_is_feasible: boolean;
  n_candidates: number;
  n_replications: number;
  is_test_data: boolean;
}

export async function fetchRecentRuns(name: string, housingCapacity: number, isolationSlots: number, interventionBudget: number): Promise<PreviousRun[]> {
  if (STATIC_MODE) return [];
  const params = new URLSearchParams({
    name,
    housing_capacity: String(housingCapacity),
    isolation_slots: String(isolationSlots),
    intervention_budget: String(interventionBudget),
  });
  const r = await fetch(`${API}/runs/recent?${params}`);
  if (!r.ok) return [];
  return r.json();
}

export async function fetchRunHistory(limit = 10): Promise<PreviousRun[]> {
  if (STATIC_MODE) return [];
  const r = await fetch(`${API}/runs/recent?limit=${limit}`);
  if (!r.ok) return [];
  return r.json();
}

export interface AnalyticsData {
  total_runs: number;
  avg_overflow: number;
  best_overflow: number;
  avg_allocation: {
    foster_support: number;
    clinic_hours: number;
    temporary_isolation: number;
    adoption_events: number;
  };
}

export async function fetchAnalytics(): Promise<AnalyticsData | null> {
  if (STATIC_MODE) return null;
  const r = await fetch(`${API}/runs/analytics`);
  if (!r.ok) return null;
  const data = await r.json();
  if (!data || !data.total_runs) return null;
  return data;
}

export interface CompareResult { winner: EvaluationResult; baselines: Record<string, EvaluationResult> }

export async function optimizeBuilderCompare(s: CustomScenarioParams, reps = 16): Promise<CompareResult> {
  if (STATIC_MODE) throw new Error(STATIC_MSG);
  const r = await fetch(`${API}/optimize/builder/compare`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ ...s, n_replications: reps }) });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

/** GET /sensitivity/builder - 6 points (3 params x high/low) merged into 3 tornado rows */
export async function getSensitivity(s: CustomScenarioParams): Promise<SensitivityResult[]> {
  if (STATIC_MODE) return [];
  const r = await fetch(`${API}/sensitivity/builder`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ...s, n_replications: 16 }),
  });
  if (!r.ok) return [];
  const points: { param: string; direction: string; mean_overflow_cat_days: number }[] = await r.json();
  // Merge high/low pairs into single tornado rows
  const map: Record<string, Partial<SensitivityResult>> = {};
  for (const p of points) {
    if (!map[p.param]) map[p.param] = { parameter: p.param, base_overflow: 0 };
    if (p.direction === "low") map[p.param].low_overflow = p.mean_overflow_cat_days;
    if (p.direction === "high") map[p.param].high_overflow = p.mean_overflow_cat_days;
  }
  return Object.values(map).map(row => ({
    parameter: row.parameter!,
    low_overflow: row.low_overflow ?? 0,
    base_overflow: row.base_overflow ?? 0,
    high_overflow: row.high_overflow ?? 0,
  }));
}

/** POST /simulate/timeline/builder - daily housing usage for the user's custom scenario */
export async function getTimeline(s: CustomScenarioParams, allocation?: { foster_support: number; clinic_hours: number; temporary_isolation: number; adoption_events: number }): Promise<DailySnapshot[]> {
  if (STATIC_MODE) return [];
  const r = await fetch(`${API}/simulate/timeline/builder`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ...s, allocation, n_replications: 1 }),
  });
  if (!r.ok) return [];
  return r.json();
}

/** POST /simulate/timeline/builder/compare - before (zero alloc) vs after (given alloc) */
export async function getTimelineCompare(s: CustomScenarioParams, allocation: { foster_support: number; clinic_hours: number; temporary_isolation: number; adoption_events: number }): Promise<{ before: DailySnapshot[]; after: DailySnapshot[] }> {
  if (STATIC_MODE) return { before: [], after: [] };
  const r = await fetch(`${API}/simulate/timeline/builder/compare`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ...s, allocation, n_replications: 1 }),
  });
  if (!r.ok) return { before: [], after: [] };
  return r.json();
}
