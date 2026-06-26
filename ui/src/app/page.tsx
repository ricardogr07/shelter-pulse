"use client";

import { useState } from "react";
import { simulate, optimize, getBaselines, exportUrl, apiBase } from "@/api";
import type { AllocationIn, EvaluationResult } from "@/types";

type Step = "configure" | "baseline" | "bottleneck" | "optimize" | "compare" | "export";

interface CompareRow {
  label: string;
  result: EvaluationResult;
  isWinner: boolean;
}

const ZERO_ALLOC: AllocationIn = {
  foster_support: 0,
  clinic_hours: 0,
  temporary_isolation: 0,
  adoption_events: 0,
};

function fmt(n: number) {
  return n.toLocaleString("en-US", { maximumFractionDigits: 1 });
}

function fmtUSD(n: number) {
  return `$${n.toLocaleString("en-US", { maximumFractionDigits: 0 })}`;
}

function Bar({ value, total, color }: { value: number; total: number; color: string }) {
  const pct = total > 0 ? (value / total) * 100 : 0;
  return (
    <div className="h-4 w-full bg-zinc-200 dark:bg-zinc-700 rounded overflow-hidden">
      <div className={`h-full ${color} transition-all`} style={{ width: `${pct}%` }} />
    </div>
  );
}

function StepHeader({ step, label }: { step: number; label: string }) {
  return (
    <div className="flex items-center gap-3 mb-6">
      <span className="flex items-center justify-center w-8 h-8 rounded-full bg-amber-500 text-white font-bold text-sm shrink-0">
        {step}
      </span>
      <h2 className="text-2xl font-bold text-zinc-900 dark:text-zinc-50">{label}</h2>
    </div>
  );
}

function Btn({ onClick, children, disabled }: { onClick: () => void; children: React.ReactNode; disabled?: boolean }) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className="mt-6 px-6 py-2.5 bg-amber-500 hover:bg-amber-400 disabled:opacity-50 disabled:cursor-not-allowed text-white font-semibold rounded-lg transition-colors"
    >
      {children}
    </button>
  );
}

export default function Home() {
  const [step, setStep] = useState<Step>("configure");
  const [baseline, setBaseline] = useState<EvaluationResult | null>(null);
  const [sweepResults, setSweepResults] = useState<EvaluationResult[] | null>(null);
  const [compareRows, setCompareRows] = useState<CompareRow[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function runBaseline() {
    setLoading(true);
    setError(null);
    try {
      const result = await simulate(ZERO_ALLOC, 32);
      setBaseline(result);
      setStep("baseline");
    } catch (e) {
      setError(e instanceof Error ? e.message : "API unreachable — is the backend running?");
    } finally {
      setLoading(false);
    }
  }

  async function runOptimize() {
    setLoading(true);
    setError(null);
    try {
      const results = await optimize(20, 32, true);
      setSweepResults(results);
      setStep("optimize");
    } catch (e) {
      setError(e instanceof Error ? e.message : "API unreachable — is the backend running?");
    } finally {
      setLoading(false);
    }
  }

  async function runCompare() {
    setLoading(true);
    setError(null);
    try {
      const baselines = await getBaselines();
      const winner = sweepResults![0];
      const baselineKeys = Object.keys(baselines);
      const baselineResults = await Promise.all(
        baselineKeys.map((k) => simulate(baselines[k], 32))
      );
      const rows: CompareRow[] = [
        { label: "BO Winner", result: winner, isWinner: true },
        ...baselineKeys.map((k, i) => ({ label: k, result: baselineResults[i], isWinner: false })),
      ];
      rows.sort((a, b) => {
        const diff = a.result.mean_overflow_cat_days - b.result.mean_overflow_cat_days;
        return diff !== 0 ? diff : a.result.mean_total_cost - b.result.mean_total_cost;
      });
      setCompareRows(rows);
      setStep("compare");
    } catch (e) {
      setError(e instanceof Error ? e.message : "API unreachable — is the backend running?");
    } finally {
      setLoading(false);
    }
  }

  async function downloadExport() {
    setError(null);
    try {
      const r = await fetch(exportUrl(), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ n_candidates: 20, n_replications: 32, use_bo: true }),
      });
      if (!r.ok) throw new Error(await r.text());
      const blob = await r.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      const disposition = r.headers.get("content-disposition") ?? "";
      const match = /filename="?([^"]+)"?/.exec(disposition);
      a.download = match ? match[1] : "shelterpulse_results.zip";
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Export failed — is the backend running?");
    }
  }

  const winner = sweepResults?.[0] ?? null;

  return (
    <main className="min-h-screen bg-zinc-50 dark:bg-zinc-950 px-4 py-12">
      <div className="max-w-2xl mx-auto space-y-2">
        {/* Header */}
        <div className="mb-8 text-center">
          <h1 className="text-4xl font-bold text-zinc-900 dark:text-zinc-50">🐱 ShelterPulse</h1>
          <p className="mt-1 text-zinc-500 dark:text-zinc-400 text-sm">
            Kitten season resource optimizer · Whisker Haven demo
          </p>
        </div>

        {/* Step progress */}
        <div className="flex gap-1 mb-8">
          {(["configure", "baseline", "bottleneck", "optimize", "compare", "export"] as Step[]).map((s, i) => (
            <div
              key={s}
              className={`h-1.5 flex-1 rounded-full ${
                s === step
                  ? "bg-amber-500"
                  : ["configure", "baseline", "bottleneck", "optimize", "compare", "export"].indexOf(step) > i
                  ? "bg-amber-300"
                  : "bg-zinc-200 dark:bg-zinc-700"
              }`}
            />
          ))}
        </div>

        {/* Error banner */}
        {error && (
          <div className="rounded-lg bg-red-50 dark:bg-red-950 border border-red-200 dark:border-red-800 p-4 text-red-700 dark:text-red-300 text-sm mb-4">
            ⚠️ {error}
          </div>
        )}

        {/* Card */}
        <div className="bg-white dark:bg-zinc-900 rounded-2xl shadow-sm border border-zinc-200 dark:border-zinc-800 p-8">

          {/* Step 1: Configure */}
          {step === "configure" && (
            <div>
              <StepHeader step={1} label="Scenario Configuration" />
              <dl className="space-y-3 text-sm">
                {[
                  ["Scenario", "Whisker Haven"],
                  ["Simulation duration", "90 days (kitten season)"],
                  ["Housing capacity", "80 cats"],
                  ["Isolation slots", "12"],
                  ["Intervention budget", "$5,000"],
                ].map(([k, v]) => (
                  <div key={k} className="flex justify-between">
                    <dt className="text-zinc-500 dark:text-zinc-400">{k}</dt>
                    <dd className="font-semibold text-zinc-900 dark:text-zinc-50">{v}</dd>
                  </div>
                ))}
              </dl>
              <Btn onClick={runBaseline} disabled={loading}>
                {loading ? "Running…" : "Run Baseline →"}
              </Btn>
            </div>
          )}

          {/* Step 2: Baseline */}
          {step === "baseline" && baseline && (
            <div>
              <StepHeader step={2} label="Baseline Results" />
              <p className="text-zinc-600 dark:text-zinc-400 text-sm mb-6">
                Without any intervention during kitten season:
              </p>
              <div className="space-y-4">
                <div className="rounded-xl bg-zinc-50 dark:bg-zinc-800 p-5 text-center">
                  <p className="text-4xl font-bold text-red-500">{fmt(baseline.mean_overflow_cat_days)}</p>
                  <p className="text-zinc-500 dark:text-zinc-400 text-sm mt-1">overflow cat-days</p>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-zinc-500 dark:text-zinc-400">Mean total cost</span>
                  <span className="font-semibold text-zinc-900 dark:text-zinc-50">{fmtUSD(baseline.mean_total_cost)}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-zinc-500 dark:text-zinc-400">Feasible</span>
                  <span className={baseline.is_feasible ? "text-green-600 font-semibold" : "text-red-500 font-semibold"}>
                    {baseline.is_feasible ? "✓ Yes" : "✗ No"}
                  </span>
                </div>
              </div>
              <Btn onClick={() => setStep("bottleneck")}>See bottlenecks →</Btn>
            </div>
          )}

          {/* Step 3: Bottleneck */}
          {step === "bottleneck" && (
            <div>
              <StepHeader step={3} label="Where Cats Get Stuck" />
              <div className="space-y-4">
                <div className="rounded-xl border border-zinc-200 dark:border-zinc-700 p-5">
                  <h3 className="font-semibold text-zinc-900 dark:text-zinc-50 mb-1">🏠 Isolation queue</h3>
                  <p className="text-zinc-500 dark:text-zinc-400 text-sm mb-3">
                    23% of intake requires 14-day isolation. 12 shared slots creates a bottleneck during surge.
                  </p>
                  <Bar value={23} total={100} color="bg-orange-400" />
                  <p className="text-xs text-zinc-400 mt-1">23% of intake routed to isolation</p>
                </div>
                <div className="rounded-xl border border-zinc-200 dark:border-zinc-700 p-5">
                  <h3 className="font-semibold text-zinc-900 dark:text-zinc-50 mb-1">🩺 Medical clearance</h3>
                  <p className="text-zinc-500 dark:text-zinc-400 text-sm mb-3">
                    Vet tech utilization peaks during kitten season (1.5 FTE), delaying cats from reaching adoption-ready status.
                  </p>
                  <Bar value={87} total={100} color="bg-red-400" />
                  <p className="text-xs text-zinc-400 mt-1">~87% vet tech utilization at peak</p>
                </div>
              </div>
              <Btn onClick={runOptimize} disabled={loading}>
                {loading ? "Optimizing… (this takes ~30s)" : "Optimize budget →"}
              </Btn>
            </div>
          )}

          {/* Step 4: Optimize */}
          {step === "optimize" && winner && (
            <div>
              <StepHeader step={4} label="Optimal Budget Allocation" />
              <div className="rounded-xl bg-zinc-50 dark:bg-zinc-800 p-5 text-center mb-6">
                <p className="text-4xl font-bold text-green-500">{fmt(winner.mean_overflow_cat_days)}</p>
                <p className="text-zinc-500 dark:text-zinc-400 text-sm mt-1">overflow cat-days (best allocation)</p>
                {baseline && baseline.mean_overflow_cat_days > 0 && winner.mean_overflow_cat_days < baseline.mean_overflow_cat_days && (
                  <p className="text-green-600 font-semibold text-sm mt-2">
                    ↓ {fmt(((baseline.mean_overflow_cat_days - winner.mean_overflow_cat_days) / baseline.mean_overflow_cat_days) * 100)}% reduction from baseline
                  </p>
                )}
              </div>
              <div className="space-y-3 text-sm">
                {(
                  [
                    ["Foster support", winner.foster_support, "bg-blue-400"],
                    ["Extra clinic hours", winner.clinic_hours, "bg-purple-400"],
                    ["Temporary isolation", winner.temporary_isolation, "bg-orange-400"],
                    ["Adoption events", winner.adoption_events, "bg-green-400"],
                  ] as [string, number, string][]
                ).map(([label, val, color]) => {
                  const total = winner.foster_support + winner.clinic_hours + winner.temporary_isolation + winner.adoption_events;
                  return (
                    <div key={label}>
                      <div className="flex justify-between mb-1">
                        <span className="text-zinc-600 dark:text-zinc-400">{label}</span>
                        <span className="font-semibold text-zinc-900 dark:text-zinc-50">{fmtUSD(val * 5000)}</span>
                      </div>
                      <Bar value={val} total={total} color={color} />
                    </div>
                  );
                })}
              </div>
              <Btn onClick={runCompare} disabled={loading}>
                {loading ? "Fetching baselines…" : "Compare to baselines →"}
              </Btn>
            </div>
          )}

          {/* Step 5: Compare */}
          {step === "compare" && compareRows && (
            <div>
              <StepHeader step={5} label="Strategy Comparison" />
              <div className="overflow-x-auto -mx-2">
                <table className="w-full text-xs border-collapse">
                  <thead>
                    <tr className="text-left text-zinc-500 dark:text-zinc-400 border-b border-zinc-200 dark:border-zinc-700">
                      <th className="py-2 px-2 font-medium">Strategy</th>
                      <th className="py-2 px-2 font-medium text-right">Foster</th>
                      <th className="py-2 px-2 font-medium text-right">Clinic</th>
                      <th className="py-2 px-2 font-medium text-right">Iso</th>
                      <th className="py-2 px-2 font-medium text-right">Events</th>
                      <th className="py-2 px-2 font-medium text-right">Overflow</th>
                      <th className="py-2 px-2 font-medium text-right">Cost</th>
                    </tr>
                  </thead>
                  <tbody>
                    {compareRows.map((row) => {
                      const t = row.result.foster_support + row.result.clinic_hours + row.result.temporary_isolation + row.result.adoption_events;
                      const pct = (v: number) => t > 0 ? `${((v / t) * 100).toFixed(0)}%` : "—";
                      return (
                        <tr
                          key={row.label}
                          className={`border-b border-zinc-100 dark:border-zinc-800 ${
                            row.isWinner ? "bg-green-50 dark:bg-green-950" : ""
                          }`}
                        >
                          <td className="py-2 px-2 font-medium text-zinc-900 dark:text-zinc-50">
                            {row.isWinner && <span className="mr-1">🏆</span>}
                            {row.label}
                          </td>
                          <td className="py-2 px-2 text-right text-zinc-600 dark:text-zinc-400">{pct(row.result.foster_support)}</td>
                          <td className="py-2 px-2 text-right text-zinc-600 dark:text-zinc-400">{pct(row.result.clinic_hours)}</td>
                          <td className="py-2 px-2 text-right text-zinc-600 dark:text-zinc-400">{pct(row.result.temporary_isolation)}</td>
                          <td className="py-2 px-2 text-right text-zinc-600 dark:text-zinc-400">{pct(row.result.adoption_events)}</td>
                          <td className="py-2 px-2 text-right font-semibold text-zinc-900 dark:text-zinc-50">{fmt(row.result.mean_overflow_cat_days)}</td>
                          <td className="py-2 px-2 text-right text-zinc-600 dark:text-zinc-400">{fmtUSD(row.result.mean_total_cost)}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
              <Btn onClick={() => setStep("export")}>Export results →</Btn>
            </div>
          )}

          {/* Step 6: Export */}
          {step === "export" && (
            <div>
              <StepHeader step={6} label="Export & Share" />
              <p className="text-zinc-500 dark:text-zinc-400 text-sm mb-6">
                Results include YAML + CSV with full reproducibility metadata.
              </p>
              <div className="space-y-3">
                <button
                  onClick={downloadExport}
                  className="w-full py-3 bg-amber-500 hover:bg-amber-400 text-white font-semibold rounded-lg transition-colors"
                >
                  ⬇ Download Results
                </button>
                <a
                  href={`${apiBase}/docs`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="block w-full py-3 text-center border border-zinc-300 dark:border-zinc-600 text-zinc-700 dark:text-zinc-300 font-semibold rounded-lg hover:bg-zinc-50 dark:hover:bg-zinc-800 transition-colors"
                >
                  🔗 Explore the API →
                </a>
              </div>
            </div>
          )}
        </div>
      </div>
    </main>
  );
}
