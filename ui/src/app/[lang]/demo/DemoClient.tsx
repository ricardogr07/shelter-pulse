"use client";

import { useState } from "react";
import { simulate, optimize, getBaselines, exportUrl, apiBase } from "@/api";
import { getDictionary } from "@/i18n/dictionaries";
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

export default function DemoClient({ lang }: { lang: string }) {
  const t = getDictionary(lang);

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
      const results = await optimize(10, 16, true);
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
      rows.sort((a, b) => a.result.mean_overflow_cat_days - b.result.mean_overflow_cat_days);
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
        body: JSON.stringify({ n_candidates: 10, n_replications: 16, use_bo: true }),
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
        <div className="mb-8 text-center">
          <h1 className="text-4xl font-bold text-zinc-900 dark:text-zinc-50">🐱 ShelterPulse</h1>
          <p className="mt-1 text-zinc-500 dark:text-zinc-400 text-sm">
            Kitten season resource optimizer · Whisker Haven demo
          </p>
        </div>

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

        {error && (
          <div className="rounded-lg bg-red-50 dark:bg-red-950 border border-red-200 dark:border-red-800 p-4 text-red-700 dark:text-red-300 text-sm mb-4">
            ⚠️ {error}
          </div>
        )}

        <div className="bg-white dark:bg-zinc-900 rounded-2xl shadow-sm border border-zinc-200 dark:border-zinc-800 p-8">

          {step === "configure" && (
            <div>
              <StepHeader step={1} label={t.demo.configTitle} />
              <p className="text-zinc-600 dark:text-zinc-400 text-sm mb-5">
                Whisker Haven is a mid-size shelter with 35 housing slots, 5 isolation slots, and 8 foster places. During kitten season (weeks 3–8), intake surges 2.5× to ~9.5 cats/day.
              </p>
              <dl className="space-y-3 text-sm">
                {[
                  ["Scenario", "Whisker Haven"],
                  ["Simulation duration", "90 days"],
                  [t.demo.housingCap, "35 cats"],
                  [t.demo.isoSlots, "5"],
                  [t.demo.fosterPlaces, "8"],
                  [t.demo.kittenSurge, "2.5×"],
                  [t.demo.budget, "$5,000"],
                ].map(([k, v]) => (
                  <div key={k} className="flex justify-between">
                    <dt className="text-zinc-500 dark:text-zinc-400">{k}</dt>
                    <dd className="font-semibold text-zinc-900 dark:text-zinc-50">{v}</dd>
                  </div>
                ))}
              </dl>
              <Btn onClick={runBaseline} disabled={loading}>
                {loading ? "Running…" : t.demo.btnBaseline + " →"}
              </Btn>
            </div>
          )}

          {step === "baseline" && baseline && (
            <div>
              <StepHeader step={2} label={t.demo.baselineTitle} />
              <p className="text-zinc-600 dark:text-zinc-400 text-sm mb-6">{t.demo.baselineDesc}</p>
              <div className="space-y-4">
                <div className="rounded-xl bg-zinc-50 dark:bg-zinc-800 p-5 text-center">
                  <p className="text-4xl font-bold text-red-500">{fmt(baseline.mean_overflow_cat_days)}</p>
                  <p className="text-zinc-500 dark:text-zinc-400 text-sm mt-1">{t.demo.overflow}</p>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-zinc-500 dark:text-zinc-400">{t.demo.budgetUsed}</span>
                  <span className="font-semibold text-zinc-900 dark:text-zinc-50">$0 of $5,000</span>
                </div>
              </div>
              <Btn onClick={() => setStep("bottleneck")}>See bottlenecks →</Btn>
            </div>
          )}

          {step === "bottleneck" && (
            <div>
              <StepHeader step={3} label={t.demo.bottleneckTitle} />
              <div className="space-y-4">
                <div className="rounded-xl border border-zinc-200 dark:border-zinc-700 p-5">
                  <h3 className="font-semibold text-zinc-900 dark:text-zinc-50 mb-1">🏠 Isolation queue</h3>
                  <p className="text-zinc-500 dark:text-zinc-400 text-sm mb-3">{t.demo.isoDesc}</p>
                  <Bar value={8} total={100} color="bg-orange-400" />
                </div>
                <div className="rounded-xl border border-zinc-200 dark:border-zinc-700 p-5">
                  <h3 className="font-semibold text-zinc-900 dark:text-zinc-50 mb-1">📈 Throughput crunch</h3>
                  <p className="text-zinc-500 dark:text-zinc-400 text-sm mb-3">{t.demo.throughputDesc}</p>
                  <Bar value={95} total={100} color="bg-red-400" />
                </div>
              </div>
              <Btn onClick={runOptimize} disabled={loading}>
                {loading ? "Optimizing…" : t.demo.btnOptimize + " →"}
              </Btn>
            </div>
          )}

          {step === "optimize" && winner && (
            <div>
              <StepHeader step={4} label={t.demo.optTitle} />
              <p className="text-zinc-600 dark:text-zinc-400 text-sm mb-4">{t.demo.optDesc}</p>
              <div className="rounded-xl bg-zinc-50 dark:bg-zinc-800 p-5 text-center mb-6">
                <p className="text-4xl font-bold text-green-500">{fmt(winner.mean_overflow_cat_days)}</p>
                <p className="text-zinc-500 dark:text-zinc-400 text-sm mt-1">{t.demo.overflow}</p>
                {baseline && baseline.mean_overflow_cat_days > 0 && (
                  <p className="text-green-600 font-semibold text-sm mt-2">
                    {t.demo.reduction}: {fmt(baseline.mean_overflow_cat_days)} → {fmt(winner.mean_overflow_cat_days)}
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
                  const dollars = total > 0 ? Math.round((val / total) * 5000) : 0;
                  return (
                    <div key={label}>
                      <div className="flex justify-between mb-1">
                        <span className="text-zinc-600 dark:text-zinc-400">{label}</span>
                        <span className="font-semibold text-zinc-900 dark:text-zinc-50">${dollars.toLocaleString()} of $5,000</span>
                      </div>
                      <Bar value={val} total={total} color={color} />
                    </div>
                  );
                })}
              </div>
              <Btn onClick={runCompare} disabled={loading}>
                {loading ? "Fetching baselines…" : t.demo.compareTitle + " →"}
              </Btn>
            </div>
          )}

          {step === "compare" && compareRows && (
            <div>
              <StepHeader step={5} label={t.demo.compareTitle} />
              <div className="overflow-x-auto -mx-2">
                <table className="w-full text-xs border-collapse">
                  <thead>
                    <tr className="text-left text-zinc-500 dark:text-zinc-400 border-b border-zinc-200 dark:border-zinc-700">
                      <th className="py-2 px-2 font-medium">{t.demo.strategy}</th>
                      <th className="py-2 px-2 font-medium text-right">Foster</th>
                      <th className="py-2 px-2 font-medium text-right">Clinic</th>
                      <th className="py-2 px-2 font-medium text-right">Iso</th>
                      <th className="py-2 px-2 font-medium text-right">Events</th>
                      <th className="py-2 px-2 font-medium text-right">{t.demo.overflow}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {compareRows.map((row) => {
                      const tot = row.result.foster_support + row.result.clinic_hours + row.result.temporary_isolation + row.result.adoption_events;
                      const pct = (v: number) => tot > 0 ? `${((v / tot) * 100).toFixed(0)}%` : "—";
                      return (
                        <tr
                          key={row.label}
                          className={`border-b border-zinc-100 dark:border-zinc-800 ${row.isWinner ? "bg-green-50 dark:bg-green-950" : ""}`}
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
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
              <Btn onClick={() => setStep("export")}>{t.demo.exportTitle} →</Btn>
            </div>
          )}

          {step === "export" && (
            <div>
              <StepHeader step={6} label={t.demo.exportTitle} />
              <p className="text-zinc-500 dark:text-zinc-400 text-sm mb-6">{t.demo.exportDesc}</p>
              <div className="space-y-3">
                <button
                  onClick={downloadExport}
                  className="w-full py-3 bg-amber-500 hover:bg-amber-400 text-white font-semibold rounded-lg transition-colors"
                >
                  ⬇ {t.demo.btnDownload}
                </button>
                <a
                  href={`${apiBase}/docs`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="block w-full py-3 text-center border border-zinc-300 dark:border-zinc-600 text-zinc-700 dark:text-zinc-300 font-semibold rounded-lg hover:bg-zinc-50 dark:hover:bg-zinc-800 transition-colors"
                >
                  🔗 {t.demo.btnApi} →
                </a>
              </div>
            </div>
          )}
        </div>
      </div>
    </main>
  );
}
