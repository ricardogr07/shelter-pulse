"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { simulateWhatIf, type CustomScenarioParams } from "@/api";

interface Props {
  scenario: CustomScenarioParams;
  winnerAllocation: {
    foster_support: number;
    clinic_hours: number;
    temporary_isolation: number;
    adoption_events: number;
  };
  originalOverflow: number;
}

interface SliderConfig {
  key: keyof CustomScenarioParams;
  label: string;
  min: number;
  max: number;
  step: number;
  format: (v: number) => string;
}

function fmt(n: number): string {
  return n.toLocaleString(undefined, { maximumFractionDigits: 1 });
}

export function WhatIfPanel({ scenario, winnerAllocation, originalOverflow }: Props) {
  const [params, setParams] = useState({
    housing_capacity: scenario.housing_capacity,
    mean_intake_per_day: scenario.mean_intake_per_day,
    intervention_budget: scenario.intervention_budget,
  });
  const [projectedOverflow, setProjectedOverflow] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const sliders: SliderConfig[] = [
    {
      key: "housing_capacity",
      label: "Housing Capacity",
      min: Math.max(10, Math.round(scenario.housing_capacity * 0.5)),
      max: Math.round(scenario.housing_capacity * 2),
      step: 1,
      format: (v) => `${v} beds`,
    },
    {
      key: "mean_intake_per_day",
      label: "Daily Intake Rate",
      min: Math.max(0.5, Math.round(scenario.mean_intake_per_day * 0.3 * 10) / 10),
      max: Math.round(scenario.mean_intake_per_day * 2.5 * 10) / 10,
      step: 0.1,
      format: (v) => `${v.toFixed(1)} cats/day`,
    },
    {
      key: "intervention_budget",
      label: "Intervention Budget",
      min: Math.max(500, Math.round(scenario.intervention_budget * 0.2)),
      max: Math.round(scenario.intervention_budget * 3),
      step: 100,
      format: (v) => `$${v.toLocaleString()}`,
    },
  ];

  const runSimulation = useCallback(async (tweaked: typeof params) => {
    setLoading(true);
    try {
      const modifiedScenario: CustomScenarioParams = {
        ...scenario,
        housing_capacity: tweaked.housing_capacity,
        mean_intake_per_day: tweaked.mean_intake_per_day,
        intervention_budget: tweaked.intervention_budget,
      };
      const result = await simulateWhatIf(modifiedScenario, winnerAllocation);
      setProjectedOverflow(result.mean_overflow_cat_days);
    } catch {
      // Silently fail - user can keep adjusting
    } finally {
      setLoading(false);
    }
  }, [scenario, winnerAllocation]);

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      runSimulation(params);
    }, 400);
    return () => { if (debounceRef.current) clearTimeout(debounceRef.current); };
  }, [params, runSimulation]);

  function handleSliderChange(key: keyof typeof params, value: number) {
    setParams((prev) => ({ ...prev, [key]: value }));
  }

  const delta = projectedOverflow !== null ? projectedOverflow - originalOverflow : null;
  const pctChange = delta !== null && originalOverflow > 0 ? (delta / originalOverflow) * 100 : null;

  return (
    <div className="mt-6 p-5 bg-gradient-to-r from-indigo-50 to-violet-50 dark:from-indigo-950/30 dark:to-violet-950/30 rounded-xl border border-indigo-200 dark:border-indigo-800/50">
      <h3 className="text-base font-bold text-indigo-900 dark:text-indigo-100 flex items-center gap-2 mb-4">
        <span>🔮</span> What If?
      </h3>
      <p className="text-xs text-indigo-600 dark:text-indigo-400 mb-4">
        Drag to see how changing parameters affects overflow with the current winning allocation.
      </p>

      <div className="space-y-4">
        {sliders.map((slider) => {
          const value = params[slider.key as keyof typeof params] as number;
          const baseValue = scenario[slider.key] as number;
          const isChanged = value !== baseValue;
          return (
            <div key={slider.key}>
              <div className="flex justify-between text-xs mb-1">
                <span className={`font-medium ${isChanged ? "text-indigo-800 dark:text-indigo-200" : "text-zinc-600 dark:text-zinc-400"}`}>
                  {slider.label}
                </span>
                <span className={`font-mono ${isChanged ? "text-indigo-700 dark:text-indigo-300 font-semibold" : "text-zinc-500 dark:text-zinc-400"}`}>
                  {slider.format(value)}
                </span>
              </div>
              <input
                type="range"
                min={slider.min}
                max={slider.max}
                step={slider.step}
                value={value}
                onChange={(e) => handleSliderChange(slider.key as keyof typeof params, parseFloat(e.target.value))}
                className="w-full h-2 bg-indigo-200 dark:bg-indigo-800 rounded-lg appearance-none cursor-pointer accent-indigo-600 dark:accent-indigo-400"
              />
              <div className="flex justify-between text-[10px] text-zinc-400 dark:text-zinc-500 mt-0.5">
                <span>{slider.format(slider.min)}</span>
                <span>{slider.format(slider.max)}</span>
              </div>
            </div>
          );
        })}
      </div>

      {/* Results comparison */}
      <div className="mt-5 pt-4 border-t border-indigo-200 dark:border-indigo-700/50">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <p className="text-[10px] uppercase tracking-wide text-zinc-500 dark:text-zinc-400">Original</p>
            <p className="text-lg font-bold text-zinc-900 dark:text-zinc-100">{fmt(originalOverflow)}</p>
            <p className="text-[10px] text-zinc-500 dark:text-zinc-400">cat-days overflow</p>
          </div>
          <div>
            <p className="text-[10px] uppercase tracking-wide text-zinc-500 dark:text-zinc-400">
              Projected {loading && <span className="inline-block w-2 h-2 bg-indigo-400 rounded-full animate-pulse ml-1"></span>}
            </p>
            {projectedOverflow !== null ? (
              <>
                <p className="text-lg font-bold text-zinc-900 dark:text-zinc-100">{fmt(projectedOverflow)}</p>
                <p className="text-[10px] text-zinc-500 dark:text-zinc-400">
                  cat-days overflow
                  {pctChange !== null && (
                    <span className={`ml-1 font-semibold ${pctChange <= 0 ? "text-green-600 dark:text-green-400" : "text-red-500 dark:text-red-400"}`}>
                      ({pctChange > 0 ? "+" : ""}{pctChange.toFixed(0)}%)
                    </span>
                  )}
                </p>
              </>
            ) : (
              <p className="text-lg font-bold text-zinc-400 dark:text-zinc-600">--</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
