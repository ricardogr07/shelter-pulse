"use client";

import type { EvaluationResult } from "@/types";

interface Props {
  results: EvaluationResult[];
}

/** Compute the Pareto frontier: points not dominated on both cost and overflow. */
function computeFrontier(points: EvaluationResult[]): EvaluationResult[] {
  const sorted = [...points].sort((a, b) => a.mean_total_cost - b.mean_total_cost);
  const front: EvaluationResult[] = [];
  let minOverflow = Infinity;
  for (const p of sorted) {
    if (p.mean_overflow_cat_days < minOverflow) {
      front.push(p);
      minOverflow = p.mean_overflow_cat_days;
    }
  }
  return front;
}

function strategyLabel(r: EvaluationResult): string {
  const parts: string[] = [];
  if (r.foster_support > 0.3) parts.push("Foster-heavy");
  if (r.adoption_events > 0.3) parts.push("Events-heavy");
  if (r.temporary_isolation > 0.3) parts.push("Isolation-heavy");
  if (r.clinic_hours > 0.3) parts.push("Clinic-heavy");
  if (parts.length === 0) parts.push("Balanced");
  return parts.join(", ");
}

// SVG layout constants
const W = 480;
const H = 280;
const PAD = { top: 20, right: 20, bottom: 40, left: 55 };
const PLOT_W = W - PAD.left - PAD.right;
const PLOT_H = H - PAD.top - PAD.bottom;

export default function ParetoChart({ results }: Props) {
  if (results.length < 2) return null;

  const frontier = computeFrontier(results);
  const frontierSet = new Set(frontier.map((r) => `${r.mean_total_cost}-${r.mean_overflow_cat_days}`));

  // Compute axis ranges with padding
  const costs = results.map((r) => r.mean_total_cost);
  const overflows = results.map((r) => r.mean_overflow_cat_days);
  const minCost = Math.min(...costs);
  const maxCost = Math.max(...costs);
  const minOverflow = Math.min(...overflows);
  const maxOverflow = Math.max(...overflows);

  // Add 10% padding to ranges
  const costRange = maxCost - minCost || 1;
  const overflowRange = maxOverflow - minOverflow || 1;
  const xMin = minCost - costRange * 0.05;
  const xMax = maxCost + costRange * 0.1;
  const yMin = Math.max(0, minOverflow - overflowRange * 0.1);
  const yMax = maxOverflow + overflowRange * 0.1;

  function scaleX(cost: number): number {
    return PAD.left + ((cost - xMin) / (xMax - xMin)) * PLOT_W;
  }

  function scaleY(overflow: number): number {
    return PAD.top + ((yMax - overflow) / (yMax - yMin)) * PLOT_H;
  }

  // Build stepped frontier path
  const sortedFrontier = [...frontier].sort((a, b) => a.mean_total_cost - b.mean_total_cost);
  let frontierPath = "";
  for (let i = 0; i < sortedFrontier.length; i++) {
    const x = scaleX(sortedFrontier[i].mean_total_cost);
    const y = scaleY(sortedFrontier[i].mean_overflow_cat_days);
    if (i === 0) {
      frontierPath += `M ${x} ${y}`;
    } else {
      // Step: horizontal then vertical
      const prevY = scaleY(sortedFrontier[i - 1].mean_overflow_cat_days);
      frontierPath += ` L ${x} ${prevY} L ${x} ${y}`;
    }
  }

  // Winner = lowest overflow
  const winner = results.reduce((best, r) => r.mean_overflow_cat_days < best.mean_overflow_cat_days ? r : best);

  // Axis ticks
  const xTicks = 5;
  const yTicks = 4;
  const xTickValues = Array.from({ length: xTicks }, (_, i) => xMin + ((xMax - xMin) / (xTicks - 1)) * i);
  const yTickValues = Array.from({ length: yTicks }, (_, i) => yMin + ((yMax - yMin) / (yTicks - 1)) * i);

  const fmtCost = (v: number) => v >= 1000 ? `$${(v / 1000).toFixed(1)}k` : `$${v.toFixed(0)}`;
  const fmtOverflow = (v: number) => v.toFixed(0);

  return (
    <figure
      role="img"
      aria-label={`Pareto frontier scatter plot: ${results.length} allocations plotted by cost vs overflow. ${frontier.length} points on the efficient frontier. Best: ${winner.mean_overflow_cat_days.toFixed(1)} cat-days overflow at $${winner.mean_total_cost.toFixed(0)} cost.`}
    >
      <svg
        viewBox={`0 0 ${W} ${H}`}
        className="w-full max-w-lg"
        preserveAspectRatio="xMidYMid meet"
      >
        {/* Grid lines */}
        {yTickValues.map((v) => (
          <line
            key={`grid-y-${v}`}
            x1={PAD.left}
            y1={scaleY(v)}
            x2={W - PAD.right}
            y2={scaleY(v)}
            className="stroke-zinc-200 dark:stroke-zinc-700"
            strokeWidth="0.5"
            strokeDasharray="3 3"
          />
        ))}

        {/* Axes */}
        <line
          x1={PAD.left} y1={H - PAD.bottom}
          x2={W - PAD.right} y2={H - PAD.bottom}
          className="stroke-zinc-400 dark:stroke-zinc-500"
          strokeWidth="1"
        />
        <line
          x1={PAD.left} y1={PAD.top}
          x2={PAD.left} y2={H - PAD.bottom}
          className="stroke-zinc-400 dark:stroke-zinc-500"
          strokeWidth="1"
        />

        {/* X-axis ticks + labels */}
        {xTickValues.map((v) => (
          <g key={`xtick-${v}`}>
            <line
              x1={scaleX(v)} y1={H - PAD.bottom}
              x2={scaleX(v)} y2={H - PAD.bottom + 4}
              className="stroke-zinc-400 dark:stroke-zinc-500"
              strokeWidth="1"
            />
            <text
              x={scaleX(v)} y={H - PAD.bottom + 16}
              textAnchor="middle"
              className="fill-zinc-500 dark:fill-zinc-400 text-[9px]"
            >
              {fmtCost(v)}
            </text>
          </g>
        ))}

        {/* Y-axis ticks + labels */}
        {yTickValues.map((v) => (
          <g key={`ytick-${v}`}>
            <line
              x1={PAD.left - 4} y1={scaleY(v)}
              x2={PAD.left} y2={scaleY(v)}
              className="stroke-zinc-400 dark:stroke-zinc-500"
              strokeWidth="1"
            />
            <text
              x={PAD.left - 8} y={scaleY(v) + 3}
              textAnchor="end"
              className="fill-zinc-500 dark:fill-zinc-400 text-[9px]"
            >
              {fmtOverflow(v)}
            </text>
          </g>
        ))}

        {/* Axis titles */}
        <text
          x={PAD.left + PLOT_W / 2} y={H - 4}
          textAnchor="middle"
          className="fill-zinc-600 dark:fill-zinc-300 text-[10px] font-medium"
        >
          Mean Total Cost ($)
        </text>
        <text
          x={12} y={PAD.top + PLOT_H / 2}
          textAnchor="middle"
          className="fill-zinc-600 dark:fill-zinc-300 text-[10px] font-medium"
          transform={`rotate(-90, 12, ${PAD.top + PLOT_H / 2})`}
        >
          Overflow (cat-days)
        </text>

        {/* Frontier line */}
        {frontierPath && (
          <path
            d={frontierPath}
            fill="none"
            className="stroke-indigo-500 dark:stroke-indigo-400"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        )}

        {/* Dominated points */}
        {results.map((r, i) => {
          const key = `${r.mean_total_cost}-${r.mean_overflow_cat_days}`;
          const isOnFrontier = frontierSet.has(key);
          if (isOnFrontier) return null;
          return (
            <circle
              key={`dom-${i}`}
              cx={scaleX(r.mean_total_cost)}
              cy={scaleY(r.mean_overflow_cat_days)}
              r="4"
              className="fill-zinc-300 dark:fill-zinc-600 stroke-zinc-400 dark:stroke-zinc-500"
              strokeWidth="1"
              opacity="0.7"
            >
              <title>{strategyLabel(r)} - Cost: ${r.mean_total_cost.toFixed(0)}, Overflow: {r.mean_overflow_cat_days.toFixed(1)}</title>
            </circle>
          );
        })}

        {/* Frontier points */}
        {sortedFrontier.map((r, i) => {
          const isWinner = r === winner;
          return (
            <g key={`front-${i}`}>
              {isWinner && (
                <circle
                  cx={scaleX(r.mean_total_cost)}
                  cy={scaleY(r.mean_overflow_cat_days)}
                  r="9"
                  className="fill-none stroke-amber-400"
                  strokeWidth="2"
                  opacity="0.8"
                />
              )}
              <circle
                cx={scaleX(r.mean_total_cost)}
                cy={scaleY(r.mean_overflow_cat_days)}
                r={isWinner ? 5 : 4.5}
                className={isWinner ? "fill-amber-500 stroke-amber-600" : "fill-indigo-500 dark:fill-indigo-400 stroke-indigo-600 dark:stroke-indigo-500"}
                strokeWidth="1.5"
              >
                <title>{isWinner ? "Winner" : "Pareto-optimal"} - Cost: ${r.mean_total_cost.toFixed(0)}, Overflow: {r.mean_overflow_cat_days.toFixed(1)}</title>
              </circle>
            </g>
          );
        })}

        {/* Legend */}
        <g transform={`translate(${W - PAD.right - 110}, ${PAD.top + 4})`}>
          <circle cx="6" cy="6" r="4" className="fill-zinc-300 dark:fill-zinc-600" />
          <text x="14" y="9" className="fill-zinc-500 dark:fill-zinc-400 text-[8px]">Dominated</text>
          <circle cx="6" cy="20" r="4" className="fill-indigo-500 dark:fill-indigo-400" />
          <text x="14" y="23" className="fill-zinc-500 dark:fill-zinc-400 text-[8px]">Pareto-optimal</text>
          <circle cx="6" cy="34" r="4" className="fill-amber-500" />
          <circle cx="6" cy="34" r="7" className="fill-none stroke-amber-400" strokeWidth="1.5" />
          <text x="14" y="37" className="fill-zinc-500 dark:fill-zinc-400 text-[8px]">Winner</text>
        </g>
      </svg>
    </figure>
  );
}
