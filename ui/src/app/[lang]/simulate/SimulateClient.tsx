"use client";

import { useState } from "react";
import { simulateCustom, optimizeCustom, optimizeBuilderCompare, getSensitivity, getTimeline, getTimelineCompare, fetchRecentRuns, type SensitivityResult, type DailySnapshot, type CompareResult, type AsyncJobResponse, type PreviousRun } from "@/api";
import { getDictionary } from "@/i18n/dictionaries";
import type { EvaluationResult, CustomScenario } from "@/types";
import SensitivityChart from "@/components/SensitivityChart";
import TimelineChart from "@/components/TimelineChart";
import CIBadge from "@/components/CIBadge";
import ComparisonTable from "@/components/ComparisonTable";
import ProgressStream from "@/components/ProgressStream";

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
  const [asyncJobId, setAsyncJobId] = useState<string | null>(null);
  const [consentStorage, setConsentStorage] = useState(false);
  const [isTestData, setIsTestData] = useState(false);
  const [previousRuns, setPreviousRuns] = useState<PreviousRun[] | null>(null);
  const [previousRunsOpen, setPreviousRunsOpen] = useState(false);
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

  // Fetch previous runs for shelter matching (debounced on key param changes)
  const fetchTimeoutRef = { current: null as ReturnType<typeof setTimeout> | null };
  function checkPreviousRuns() {
    if (fetchTimeoutRef.current) clearTimeout(fetchTimeoutRef.current);
    fetchTimeoutRef.current = setTimeout(async () => {
      if (!form.name || form.name.length < 2) { setPreviousRuns(null); return; }
      try {
        const runs = await fetchRecentRuns(form.name, form.housing_capacity, form.isolation_slots, form.intervention_budget);
        setPreviousRuns(runs.length > 0 ? runs : []);
      } catch { setPreviousRuns(null); }
    }, 600);
  }

  function loadFromRun(run: PreviousRun) {
    setForm((f) => ({
      ...f,
      duration_days: run.duration_days,
      housing_capacity: run.housing_capacity,
      isolation_slots: run.isolation_slots,
      intervention_budget: run.intervention_budget,
      mean_intake_per_day: run.mean_intake_per_day,
    }));
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
    setLoading(true); setError(null); setSimResult(null); setTimelineBaseline(null); setCompareData(null); setAsyncJobId(null);
    try {
      const response = await optimizeCustom(form, 15, 16, { consent_storage: consentStorage, is_test_data: isTestData });

      // Check if async dispatch (202 with job_id)
      if ("job_id" in response) {
        setAsyncJobId((response as AsyncJobResponse).job_id);
        setLoading(false);
        return;
      }

      // Sync path: results returned directly
      const results = response as EvaluationResult[];
      await handleOptResults(results);
    }
    catch (e) { setError(e instanceof Error ? e.message : "Failed"); }
    finally { setLoading(false); }
  }

  async function handleOptResults(results: EvaluationResult[]) {
    setOptResults(results);
    setAsyncJobId(null);
    // Fetch before/after timeline with winner allocation
    if (results.length > 0) {
      const winner = results[0];
      const alloc = { foster_support: winner.foster_support, clinic_hours: winner.clinic_hours, temporary_isolation: winner.temporary_isolation, adoption_events: winner.adoption_events };
      const compare = await getTimelineCompare(form, alloc);
      setTimelineBaseline(compare.before);
      setTimeline(compare.after);
    }
  }

  function handleStreamComplete(results: EvaluationResult[]) {
    handleOptResults(results);
  }

  function handleStreamError(message: string) {
    setAsyncJobId(null);
    setError(message);
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
          <Input label={t.simulate.labels.name} tooltip={t.simulate.tooltips.name} name="name" type="text" value={form.name} onChange={set("name")} onBlur={checkPreviousRuns} />
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
          {/* Consent checkboxes */}
          <div className="bg-amber-50 dark:bg-amber-950/20 border border-amber-200 dark:border-amber-800 rounded-lg p-4">
            <h3 className="text-sm font-semibold text-amber-800 dark:text-amber-200 mb-2">
              Data &amp; Privacy
            </h3>
            <label className="flex items-start gap-2 mb-2 cursor-pointer">
              <input
                type="checkbox"
                checked={consentStorage}
                onChange={(e) => setConsentStorage(e.target.checked)}
                className="mt-0.5 rounded border-zinc-300"
              />
              <span className="text-sm text-zinc-600 dark:text-zinc-400">
                I consent to storing my optimization inputs and results for run history.{" "}
                <a href={`/${lang}/legal/privacy`} className="text-amber-600 underline">Privacy Policy</a>
              </span>
            </label>
            <label className="flex items-start gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={isTestData}
                onChange={(e) => setIsTestData(e.target.checked)}
                className="mt-0.5 rounded border-zinc-300"
              />
              <span className="text-sm text-zinc-600 dark:text-zinc-400">
                This is test/demo data (no real shelter information).
              </span>
            </label>
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

        {/* Previous runs for this shelter */}
        {previousRuns !== null && (
          <div className="mt-4 bg-white dark:bg-zinc-900 rounded-xl shadow-sm border border-zinc-200 dark:border-zinc-800 overflow-hidden">
            {previousRuns.length === 0 ? (
              <div className="p-4 text-sm text-zinc-500 dark:text-zinc-400">
                No previous runs for &quot;{form.name}&quot; with these parameters. Run your first optimization below.
              </div>
            ) : (
              <>
                <button
                  onClick={() => setPreviousRunsOpen(!previousRunsOpen)}
                  className="w-full flex items-center justify-between p-4 text-left hover:bg-zinc-50 dark:hover:bg-zinc-800/50 transition-colors"
                >
                  <span className="text-sm font-semibold text-zinc-700 dark:text-zinc-300">
                    Previous runs for &quot;{form.name}&quot; ({previousRuns.length})
                  </span>
                  <span className={`text-zinc-400 transition-transform ${previousRunsOpen ? "rotate-180" : ""}`}>
                    &#9660;
                  </span>
                </button>
                {previousRunsOpen && (
                  <div className="px-4 pb-4">
                    <div className="overflow-x-auto">
                      <table className="w-full text-sm">
                        <thead>
                          <tr className="text-left text-zinc-500 dark:text-zinc-400 border-b border-zinc-200 dark:border-zinc-700">
                            <th className="pb-2">Date</th>
                            <th className="pb-2">Overflow</th>
                            <th className="pb-2">Allocation</th>
                            <th className="pb-2"></th>
                          </tr>
                        </thead>
                        <tbody>
                          {previousRuns.map((run) => (
                            <tr key={run.job_id} className="border-b border-zinc-100 dark:border-zinc-700/50">
                              <td className="py-2 text-zinc-600 dark:text-zinc-400">
                                {new Date(run.created_at).toLocaleDateString()}
                              </td>
                              <td className="py-2 font-semibold">
                                {run.winner_mean_overflow != null ? fmt(run.winner_mean_overflow) : "-"}
                              </td>
                              <td className="py-2 text-zinc-500 text-xs">
                                F:{((run.winner_foster_support ?? 0) * 100).toFixed(0)}%
                                {" "}C:{((run.winner_clinic_hours ?? 0) * 100).toFixed(0)}%
                                {" "}I:{((run.winner_temporary_isolation ?? 0) * 100).toFixed(0)}%
                                {" "}A:{((run.winner_adoption_events ?? 0) * 100).toFixed(0)}%
                              </td>
                              <td className="py-2">
                                <button
                                  onClick={() => loadFromRun(run)}
                                  className="text-xs text-amber-600 hover:text-amber-500 underline"
                                >
                                  Load config
                                </button>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}
              </>
            )}
          </div>
        )}

        {asyncJobId && (
          <div className="mt-6 bg-white dark:bg-zinc-900 rounded-xl p-6 shadow-sm border border-zinc-200 dark:border-zinc-800">
            <h2 className="text-lg font-bold text-zinc-900 dark:text-zinc-50 mb-3">Optimizing...</h2>
            <ProgressStream
              jobId={asyncJobId}
              onComplete={handleStreamComplete}
              onError={handleStreamError}
            />
          </div>
        )}

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
            <p className="text-sm text-zinc-500 dark:text-zinc-400 mb-3">Budget: ${fmt(form.intervention_budget)} - showing how to split it across 4 intervention strategies to minimize overflow.</p>
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
