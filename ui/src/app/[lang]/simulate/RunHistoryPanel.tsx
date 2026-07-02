"use client";

import { useEffect, useState } from "react";
import { fetchAnalytics, type AnalyticsData } from "@/api";

function fmt(n: number): string {
  return n.toLocaleString(undefined, { maximumFractionDigits: 1 });
}

export function RunHistoryPanel({ refreshKey }: { refreshKey?: number }) {
  const [analytics, setAnalytics] = useState<AnalyticsData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      const data = await fetchAnalytics();
      if (!cancelled) {
        setAnalytics(data);
        setLoading(false);
      }
    }
    load();
    return () => { cancelled = true; };
  }, [refreshKey]);

  if (loading || !analytics) return null;

  return (
    <section className="mt-8 border-t border-zinc-200 dark:border-zinc-700 pt-6">
      <h2 className="text-lg font-bold text-zinc-900 dark:text-zinc-50 mb-4">Community Statistics</h2>

      <div className="p-4 bg-gradient-to-r from-amber-50 to-orange-50 dark:from-amber-950/30 dark:to-orange-950/30 rounded-xl border border-amber-200 dark:border-amber-800/50">
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-4">
          <div>
            <p className="text-xs text-amber-600 dark:text-amber-400">Total Optimizations</p>
            <p className="text-xl font-bold text-amber-900 dark:text-amber-100">{analytics.total_runs}</p>
          </div>
          <div>
            <p className="text-xs text-amber-600 dark:text-amber-400">Average Best Overflow</p>
            <p className="text-xl font-bold text-amber-900 dark:text-amber-100">{fmt(analytics.avg_overflow)} cat-days</p>
          </div>
          <div>
            <p className="text-xs text-amber-600 dark:text-amber-400">Best Result Ever</p>
            <p className="text-xl font-bold text-amber-900 dark:text-amber-100">{fmt(analytics.best_overflow)} cat-days</p>
          </div>
        </div>

        {/* Average allocation bar */}
        <p className="text-xs text-amber-600 dark:text-amber-400 mb-1">Average Winning Allocation</p>
        <div className="flex h-5 rounded-md overflow-hidden">
          <div
            className="bg-green-400 dark:bg-green-600 flex items-center justify-center text-[10px] font-medium text-white"
            style={{ width: `${(analytics.avg_allocation.foster_support * 100).toFixed(0)}%` }}
            title={`Foster: ${(analytics.avg_allocation.foster_support * 100).toFixed(0)}%`}
          >
            {(analytics.avg_allocation.foster_support * 100) >= 12 ? `F ${(analytics.avg_allocation.foster_support * 100).toFixed(0)}%` : ""}
          </div>
          <div
            className="bg-blue-400 dark:bg-blue-600 flex items-center justify-center text-[10px] font-medium text-white"
            style={{ width: `${(analytics.avg_allocation.clinic_hours * 100).toFixed(0)}%` }}
            title={`Clinic: ${(analytics.avg_allocation.clinic_hours * 100).toFixed(0)}%`}
          >
            {(analytics.avg_allocation.clinic_hours * 100) >= 12 ? `C ${(analytics.avg_allocation.clinic_hours * 100).toFixed(0)}%` : ""}
          </div>
          <div
            className="bg-purple-400 dark:bg-purple-600 flex items-center justify-center text-[10px] font-medium text-white"
            style={{ width: `${(analytics.avg_allocation.temporary_isolation * 100).toFixed(0)}%` }}
            title={`Isolation: ${(analytics.avg_allocation.temporary_isolation * 100).toFixed(0)}%`}
          >
            {(analytics.avg_allocation.temporary_isolation * 100) >= 12 ? `I ${(analytics.avg_allocation.temporary_isolation * 100).toFixed(0)}%` : ""}
          </div>
          <div
            className="bg-orange-400 dark:bg-orange-600 flex items-center justify-center text-[10px] font-medium text-white"
            style={{ width: `${(analytics.avg_allocation.adoption_events * 100).toFixed(0)}%` }}
            title={`Adoption: ${(analytics.avg_allocation.adoption_events * 100).toFixed(0)}%`}
          >
            {(analytics.avg_allocation.adoption_events * 100) >= 12 ? `A ${(analytics.avg_allocation.adoption_events * 100).toFixed(0)}%` : ""}
          </div>
        </div>
        <div className="flex gap-3 mt-1 text-[10px] text-amber-700 dark:text-amber-300">
          <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-sm bg-green-400 dark:bg-green-600 inline-block"></span>Foster</span>
          <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-sm bg-blue-400 dark:bg-blue-600 inline-block"></span>Clinic</span>
          <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-sm bg-purple-400 dark:bg-purple-600 inline-block"></span>Isolation</span>
          <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-sm bg-orange-400 dark:bg-orange-600 inline-block"></span>Adoption</span>
        </div>
      </div>
    </section>
  );
}
