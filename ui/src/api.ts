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

// Stubs — real endpoints implemented in post-merge backlog
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

// ponytail: stubs return empty until /sensitivity and /timeline endpoints land
export async function getSensitivity(_s: CustomScenarioParams): Promise<SensitivityResult[]> { return []; }
export async function getTimeline(_s: CustomScenarioParams): Promise<DailySnapshot[]> { return []; }
