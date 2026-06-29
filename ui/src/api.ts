export const apiBase = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const API = apiBase;

import type { AllocationIn, EvaluationResult } from "./types";

export async function simulate(allocation: AllocationIn, reps = 32): Promise<EvaluationResult> {
  const r = await fetch(`${API}/simulate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ allocation, n_replications: reps }),
  });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function optimize(nCandidates = 20, reps = 32, useBo = true): Promise<EvaluationResult[]> {
  const r = await fetch(`${API}/optimize`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ n_candidates: nCandidates, n_replications: reps, use_bo: useBo }),
  });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function getBaselines(): Promise<Record<string, AllocationIn>> {
  const r = await fetch(`${API}/baselines`);
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export function exportUrl(): string {
  return `${API}/export`;
}

// Stubs comment removed — these are real now
export interface SensitivityResult { parameter: string; low_overflow: number; base_overflow: number; high_overflow: number; }
export interface DailySnapshot { day: number; housing_used: number; overflow: number; }
export interface CustomScenarioParams { name: string; duration_days: number; housing_capacity: number; isolation_slots: number; vet_tech_fte: number; intervention_budget: number; mean_intake_per_day: number; kitten_fraction: number; base_adoption_rate: number; }

export async function simulateCustom(s: CustomScenarioParams): Promise<EvaluationResult> {
  const r = await fetch(`${API}/simulate/builder`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(s) });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function optimizeCustom(s: CustomScenarioParams, nCandidates = 20, reps = 32): Promise<EvaluationResult[]> {
  const r = await fetch(`${API}/optimize/builder`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ ...s, n_candidates: nCandidates, n_replications: reps }) });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

/** GET /sensitivity/builder — 6 points (3 params × high/low) merged into 3 tornado rows */
export async function getSensitivity(s: CustomScenarioParams): Promise<SensitivityResult[]> {
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

/** POST /simulate/timeline/builder — daily housing usage for the user's custom scenario */
export async function getTimeline(s: CustomScenarioParams): Promise<DailySnapshot[]> {
  const r = await fetch(`${API}/simulate/timeline/builder`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ...s, n_replications: 1 }),
  });
  if (!r.ok) return [];
  return r.json();
}
