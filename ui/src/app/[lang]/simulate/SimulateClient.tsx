"use client";

import { useState } from "react";
import { simulateCustom, optimizeCustom, optimizeBuilderCompare, getSensitivity, getTimeline, getTimelineCompare, type SensitivityResult, type DailySnapshot, type CompareResult } from "@/api";
import { getDictionary } from "@/i18n/dictionaries";
import type { EvaluationResult, CustomScenario } from "@/types";
import SensitivityChart from "@/components/SensitivityChart";
import TimelineChart from "@/components/TimelineChart";
import CIBadge from "@/components/CIBadge";
import ComparisonTable from "@/components/ComparisonTable";

const DEFAULTS: CustomScenario = {
  name: "My Shelter",
  duration_days: 90,
  housing_capacity: 80,
  isolation_slots: 12,
  vet_tech_fte: 1.5,
  intervention_budget: 5000,
  mean_intake_per_day: 3.5,
  kitten_fraction: 0.4,
  base_adoption_rate: 0.15,
};

function fmt(n: number) {
  return n.toLocaleString("en-US", { maximumFractionDigits: 1 });
}

function Input({ label, tooltip, name, type = "number", value, onChange, ...props }: {
  label: string; tooltip?: string; name: string; type?: string; value: string | number;
  onChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
  [k: string]: unknown;
}) {
  return (
    <label className="flex flex-col gap-1">
      <span className="text-sm text-zinc-600 dark:text-zinc-400" title={tooltip}>{label} {tooltip && <span className="cursor-help">ⓘ</span>}</span>
      <input
        name={name} type={type} value={value} onChange={onChange}
        className="px-3 py-2 rounded-lg bg-zinc-100 dark:bg-zinc-800 border border-zinc-300 dark:border-zinc-600 text-zinc-900 dark:text-zinc-100 focus:outline-none focus:ring-2 focus:ring-amber-500"
        {...props}
      />
    </label>
  );
}

export default function SimulateClient({ lang }: { lang: string }) {
  const t = getDictionary(lang);
  const [form, setForm] = useState<CustomScenario>(DEFAULTS);
  const [simResult, setSimResult] = useState<EvaluationResult | null>(null);
  const [optResults, setOptResults] = useState<EvaluationResult[] | null>(null);
  const [compareData, setCompareData] = useState<CompareResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [compareLoading, setCompareLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'timeline' | 'sensitivity'>('timeline');
  const [timeline, setTimeline] = useState<DailySnapshot[] | null>(null);
  const [timelineBaseline, setTimelineBaseline] = useState<DailySnapshot[] | null>(null);
  const [sensitivity, setSensitivity] = useState<SensitivityResult[] | null>(null);
  const [analyticsLoading, setAnalyticsLoading] = useState(false);

  function set(field: keyof CustomScenario) {
    return (e: React.ChangeEvent<HTMLInputElement>) => {
      const v = e.target.type === "number" ? parseFloat(e.target.value) || 0 : e.target.value;
      setForm((f) => ({ ...f, [field]: v }));
    };
  }

  async function runSimulate() {
    setLoading(true); setError(null); setOptResults(null); setTimelineBaseline(null);
    try {
      const result = await simulateCustom(form);
      setSimResult(result);
      loadTimeline();
    }
    catch (e) { setError(e instanceof Error ? e.message : "Failed"); }
    finally { setLoading(false); }
  }

  async function loadTimeline() {
    setAnalyticsLoading(true);
    try { setTimeline(await getTimeline(form)); }
    catch { /* silent */ }
    finally { setAnalyticsLoading(false); }
  }

  async function loadSensitivity() {
    setAnalyticsLoading(true);
    try { setSensitivity(await getSensitivity(form)); }
    catch { /* silent */ }
    finally { setAnalyticsLoading(false); }
  }

  async function runOptimize() {
    setLoading(true); setError(null); setSimResult(null); setTimelineBaseline(null); setCompareData(null);
    try {
      const results = await optimizeCustom(form, 15, 16);
      setOptResults(results);
      // Fetch before/after timeline with winner allocation
      if (results.length > 0) {
        const winner = results[0];
        const alloc = { foster_support: winner.foster_support, clinic_hours: winner.clinic_hours, temporary_isolation: winner.temporary_isolation, adoption_events: winner.adoption_events };
        const compare = await getTimelineCompare(form, alloc);
        setTimelineBaseline(compare.before);
        setTimeline(compare.after);
      }
    }
    catch (e) { setError(e instanceof Error ? e.message : "Failed"); }
    finally { setLoading(false); }
  }

  async function runCompare() {
    setCompareLoading(true); setError(null);
    try {
      const result = await optimizeBuilderCompare(form, 16);
      setCompareData(result);
    }
    catch (e) { setError(e instanceof Error ? e.message : "Failed"); }
    finally { setCompareLoading(false); }
  }

  const fields: { field: keyof CustomScenario; type?: string; min?: number; max?: number; step?: number }[] = [
    { field: "duration_days", min: 1, max: 365 },
    { field: "housing_capacity", min: 1, max: 500 },
    { field: "isolation_slots", min: 0, max: 100 },
    { field: "vet_tech_fte", min: 0.5, max: 10, step: 0.5 },
    { field: "intervention_budget", min: 0, max: 100000 },
    { field: "mean_intake_per_day", min: 0.1, max: 50, step: 0.1 },
    { field: "kitten_fraction", min: 0, max: 1, step: 0.01 },
    { field: "base_adoption_rate", min: 0, max: 1, step: 0.01 },
  ];

  return (
    <main className="min-h-screen bg-zinc-50 dark:bg-zinc-950 py-12 px-4">
      <div className="max-w-3xl mx-auto">
        <h1 className="text-3xl font-bold text-zinc-900 dark:text-zinc-50 mb-2">{t.simulate.title}</h1>
        <p className="text-zinc-600 dark:text-zinc-400 mb-8">{t.simulate.subtitle}</p>

        <div className="bg-white dark:bg-zinc-900 rounded-xl p-6 shadow-sm border border-zinc-200 dark:border-zinc-800 space-y-6">
          <Input label={t.simulate.labels.name} tooltip={t.simulate.tooltips.name} name="name" type="text" value={form.name} onChange={set("name")} />
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {fields.map(({ field, ...rest }) => (
              <Input
                key={field}
                label={t.simulate.labels[field] ?? field}
                tooltip={t.simulate.tooltips[field]}
                name={field}
                value={form[field] as string | number}
                onChange={set(field)}
                {...rest}
              />
            ))}
          </div>
          <div className="flex gap-4 pt-2">
            <button onClick={runSimulate} disabled={loading}
              className="px-6 py-2.5 bg-amber-500 hover:bg-amber-400 disabled:opacity-50 text-white font-semibold rounded-lg transition-colors">
              {loading ? t.common.loading : t.simulate.btnSimulate}
            </button>
            <button onClick={runOptimize} disabled={loading}
              className="px-6 py-2.5 bg-zinc-700 hover:bg-zinc-600 disabled:opacity-50 text-white font-semibold rounded-lg transition-colors">
              {loading ? t.common.loading : t.simulate.btnOptimize}
            </button>
          </div>
        </div>

        {error && <p className="mt-4 text-red-500">{error}</p>}

        {simResult && (
          <div className="mt-8 bg-white dark:bg-zinc-900 rounded-xl p-6 shadow-sm border border-zinc-200 dark:border-zinc-800">
            <h2 className="text-xl font-bold text-zinc-900 dark:text-zinc-50 mb-4">{t.simulate.resultTitle}</h2>
            <dl className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div>
                <dt className="text-sm text-zinc-500 dark:text-zinc-400">{t.simulate.overflow}</dt>
                <dd className="text-2xl font-bold text-amber-500">
                  {fmt(simResult.mean_overflow_cat_days)}
                  {simResult.ci95_overflow_low != null && (
                    <CIBadge low={simResult.ci95_overflow_low} high={simResult.ci95_overflow_high!} mean={simResult.mean_overflow_cat_days} />
                  )}
                </dd>
              </div>
              <div>
                <dt className="text-sm text-zinc-500 dark:text-zinc-400">{t.simulate.cost}</dt>
                <dd className="text-2xl font-bold text-zinc-900 dark:text-zinc-100">${fmt(form.intervention_budget)}</dd>
              </div>
              <div>
                <dt className="text-sm text-zinc-500 dark:text-zinc-400">{t.simulate.feasible}</dt>
                <dd className={`text-2xl font-bold ${simResult.is_feasible ? "text-green-500" : "text-red-500"}`}>
                  {simResult.is_feasible ? t.common.yes + " ✓" : t.common.no + " ✗"}
                </dd>
              </div>
            </dl>
          </div>
        )}

        {(simResult || (optResults && timeline)) && (
          <div className="mt-6 bg-white dark:bg-zinc-900 rounded-xl p-6 shadow-sm border border-zinc-200 dark:border-zinc-800">
            <div className="flex gap-4 mb-4 border-b border-zinc-200 dark:border-zinc-700">
              <button
                onClick={() => { setActiveTab('timeline'); if (!timeline) loadTimeline(); }}
                className={`pb-2 text-sm font-medium ${activeTab === 'timeline' ? 'text-amber-500 border-b-2 border-amber-500' : 'text-zinc-500 dark:text-zinc-400'}`}
              >
                {t.simulate.analytics?.timeline ?? 'Timeline'}
              </button>
              <button
                onClick={() => { setActiveTab('sensitivity'); if (!sensitivity) loadSensitivity(); }}
                className={`pb-2 text-sm font-medium ${activeTab === 'sensitivity' ? 'text-amber-500 border-b-2 border-amber-500' : 'text-zinc-500 dark:text-zinc-400'}`}
              >
                {t.simulate.analytics?.sensitivity ?? 'Sensitivity'}
              </button>
            </div>
            {analyticsLoading && <p className="text-sm text-zinc-500">{t.common.loading}</p>}
            {activeTab === 'timeline' && timeline && (
              <TimelineChart data={timeline} capacity={form.housing_capacity} baseline={timelineBaseline ?? undefined} />
            )}
            {activeTab === 'sensitivity' && sensitivity && (
              <SensitivityChart data={sensitivity} />
            )}
          </div>
        )}

        {optResults && (
          <div className="mt-8 bg-white dark:bg-zinc-900 rounded-xl p-6 shadow-sm border border-zinc-200 dark:border-zinc-800">
            <h2 className="text-xl font-bold text-zinc-900 dark:text-zinc-50 mb-4">{t.simulate.optResultTitle}</h2>
            <p className="text-sm text-zinc-500 dark:text-zinc-400 mb-3">Budget: ${fmt(form.intervention_budget)} — showing how to split it across 4 intervention strategies to minimize overflow.</p>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-zinc-500 dark:text-zinc-400 border-b border-zinc-200 dark:border-zinc-700">
                    <th className="pb-2">#</th>
                    <th className="pb-2">Foster</th>
                    <th className="pb-2">Clinic</th>
                    <th className="pb-2">Isolation</th>
                    <th className="pb-2">Adoption</th>
                    <th className="pb-2">{t.simulate.overflow}</th>
                    <th className="pb-2">{t.simulate.feasible}</th>
                  </tr>
                </thead>
                <tbody>
                  {optResults.slice(0, 5).map((r, i) => (
                    <tr key={i} className="border-b border-zinc-100 dark:border-zinc-700/50">
                      <td className="py-2 font-bold text-amber-500">{i + 1}</td>
                      <td className="py-2">{(r.foster_support * 100).toFixed(0)}%</td>
                      <td className="py-2">{(r.clinic_hours * 100).toFixed(0)}%</td>
                      <td className="py-2">{(r.temporary_isolation * 100).toFixed(0)}%</td>
                      <td className="py-2">{(r.adoption_events * 100).toFixed(0)}%</td>
                      <td className="py-2 font-semibold">{fmt(r.mean_overflow_cat_days)}</td>
                      <td className="py-2">{r.is_feasible ? "✓" : "✗"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <button onClick={runCompare} disabled={compareLoading}
              className="mt-4 px-5 py-2 bg-zinc-700 hover:bg-zinc-600 disabled:opacity-50 text-white text-sm font-semibold rounded-lg transition-colors">
              {compareLoading ? "Comparing…" : "Compare against baselines →"}
            </button>
          </div>
        )}

        {compareData && (
          <div className="mt-6 bg-white dark:bg-zinc-900 rounded-xl p-6 shadow-sm border border-zinc-200 dark:border-zinc-800">
            <h2 className="text-xl font-bold text-zinc-900 dark:text-zinc-50 mb-4">BO Winner vs Baselines</h2>
            <p className="text-sm text-zinc-500 dark:text-zinc-400 mb-3">Ranked by overflow cat-days. The optimizer&apos;s best allocation compared against 5 named strategies.</p>
            <ComparisonTable winner={compareData.winner} baselines={compareData.baselines} />
          </div>
        )}
      </div>
    </main>
  );
}
