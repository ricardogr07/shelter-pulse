'use client';

export interface TimelineData {
  day: number;
  housing_used: number;
  overflow: number;
}

interface Props {
  data: TimelineData[];
  capacity: number;
  baseline?: TimelineData[];
}

export default function TimelineChart({ data, capacity, baseline }: Props) {
  if (!data.length) return null;

  const allValues = [
    capacity,
    ...data.map(d => d.housing_used),
    ...(baseline ?? []).map(d => d.housing_used),
  ];
  const maxVal = Math.max(...allValues);
  const capPct = (capacity / maxVal) * 100;

  return (
    <div className="relative">
      {/* Legend */}
      {baseline && (
        <div className="flex gap-4 mb-2 text-[10px] text-zinc-500 dark:text-zinc-400">
          <span className="flex items-center gap-1">
            <span className="inline-block w-3 h-2 rounded-sm bg-zinc-300 dark:bg-zinc-600" />
            Before (no intervention)
          </span>
          <span className="flex items-center gap-1">
            <span className="inline-block w-3 h-2 rounded-sm bg-sky-400 dark:bg-sky-500" />
            After (optimized)
          </span>
        </div>
      )}

      {/* Capacity line */}
      <div
        className="absolute left-0 right-0 border-t-2 border-dashed border-amber-500 z-10"
        style={{ bottom: `${capPct}%` }}
      >
        <span className="absolute -top-4 right-0 text-[10px] text-amber-500">capacity</span>
      </div>

      {/* Bars */}
      <div className="flex items-end gap-px h-40">
        {data.map((d, i) => {
          const pct = (d.housing_used / maxVal) * 100;
          const isOverflow = d.overflow > 0;
          const baselinePct = baseline && baseline[i] ? (baseline[i].housing_used / maxVal) * 100 : 0;

          return (
            <div key={d.day} className="flex-1 relative h-full flex items-end">
              {/* Baseline bar (behind) */}
              {baseline && baseline[i] && (
                <div
                  className="absolute bottom-0 inset-x-0 rounded-t bg-zinc-300 dark:bg-zinc-600 opacity-60"
                  style={{ height: `${baselinePct}%` }}
                  title={`Day ${d.day} before: ${baseline[i].housing_used.toFixed(0)} cats`}
                />
              )}
              {/* Main bar (front) */}
              <div
                className={`relative w-full rounded-t ${isOverflow ? 'bg-red-400 dark:bg-red-500' : 'bg-sky-400 dark:bg-sky-500'}`}
                style={{ height: `${pct}%` }}
                title={`Day ${d.day}: ${d.housing_used.toFixed(0)} cats${isOverflow ? ' (OVERFLOW)' : ''}`}
              />
            </div>
          );
        })}
      </div>

      {/* Day labels */}
      <div className="flex justify-between mt-1 text-[10px] text-zinc-400">
        {data.filter((_, i) => i % 10 === 0).map(d => (
          <span key={d.day}>{d.day}</span>
        ))}
      </div>
    </div>
  );
}
