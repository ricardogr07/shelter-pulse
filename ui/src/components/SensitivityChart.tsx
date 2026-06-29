'use client';

export interface SensitivityData {
  parameter: string;
  low_overflow: number;
  base_overflow: number;
  high_overflow: number;
}

export default function SensitivityChart({ data }: { data: SensitivityData[] }) {
  if (!data.length) return null;
  const maxOverflow = Math.max(...data.flatMap(d => [d.low_overflow, d.high_overflow]));

  return (
    <div className="space-y-3">
      {data.map((row) => {
        const baseX = maxOverflow > 0 ? (row.base_overflow / maxOverflow) * 100 : 50;
        const lowX = maxOverflow > 0 ? (row.low_overflow / maxOverflow) * 100 : 0;
        const highX = maxOverflow > 0 ? (row.high_overflow / maxOverflow) * 100 : 0;
        return (
          <div key={row.parameter} className="flex items-center gap-3">
            <span className="text-xs text-zinc-600 dark:text-zinc-400 w-32 text-right truncate">{row.parameter}</span>
            <div className="flex-1 h-6 bg-zinc-100 dark:bg-zinc-800 rounded relative">
              <div
                className="absolute top-0 h-full bg-emerald-400/60 dark:bg-emerald-500/40 rounded-l"
                style={{ left: `${Math.min(lowX, baseX)}%`, width: `${Math.abs(baseX - lowX)}%` }}
              />
              <div
                className="absolute top-0 h-full bg-red-400/60 dark:bg-red-500/40 rounded-r"
                style={{ left: `${Math.min(highX, baseX)}%`, width: `${Math.abs(highX - baseX)}%` }}
              />
              <div
                className="absolute top-0 h-full w-0.5 bg-zinc-900 dark:bg-zinc-100"
                style={{ left: `${baseX}%` }}
              />
            </div>
            <span className="text-xs text-zinc-500 dark:text-zinc-400 w-16">{row.base_overflow.toFixed(0)}</span>
          </div>
        );
      })}
    </div>
  );
}
