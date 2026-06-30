'use client';

import type { EvaluationResult } from "@/types";
import CIBadge from "./CIBadge";

interface CompareRow {
  label: string;
  result: EvaluationResult;
  isWinner: boolean;
}

function fmt(n: number) {
  return n.toLocaleString("en-US", { maximumFractionDigits: 1 });
}

interface Props {
  winner: EvaluationResult;
  baselines: Record<string, EvaluationResult>;
}

export default function ComparisonTable({ winner, baselines }: Props) {
  const rows: CompareRow[] = [
    { label: "BO Winner", result: winner, isWinner: true },
    ...Object.entries(baselines).map(([name, result]) => ({
      label: name.replace(/_/g, " "),
      result,
      isWinner: false,
    })),
  ];

  rows.sort((a, b) => a.result.mean_overflow_cat_days - b.result.mean_overflow_cat_days);

  return (
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
            <th className="py-2 px-2 font-medium text-right">CI 95%</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => {
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
                <td className="py-2 px-2 text-right">
                  {row.result.ci95_overflow_low != null && row.result.ci95_overflow_high != null && (
                    <CIBadge low={row.result.ci95_overflow_low} high={row.result.ci95_overflow_high} mean={row.result.mean_overflow_cat_days} />
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
