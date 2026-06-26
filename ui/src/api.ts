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
