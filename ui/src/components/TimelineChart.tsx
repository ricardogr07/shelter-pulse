'use client';

export interface TimelineData {
  day: number;
  housing_used: number;
  overflow: number;
}

export default function TimelineChart({ data, capacity }: { data: TimelineData[]; capacity: number }) {
  if (!data.length) return null;
  const maxVal = Math.max(capacity, ...data.map(d => d.housing_used));
  const capPct = (capacity / maxVal) * 100;

  return (
    <div className="relative">
      <div
        className="absolute left-0 right-0 border-t-2 border-dashed border-amber-500 z-10"
        style={{ bottom: `${capPct}%` }}
      >
        <span className="absolute -top-4 right-0 text-[10px] text-amber-500">capacity</span>
      </div>
      <div className="flex items-end gap-px h-40">
        {data.map((d) => {
          const pct = (d.housing_used / maxVal) * 100;
          const isOverflow = d.overflow > 0;
          return (
            <div
              key={d.day}
              className={`flex-1 rounded-t ${isOverflow ? 'bg-red-400 dark:bg-red-500' : 'bg-sky-400 dark:bg-sky-500'}`}
              style={{ height: `${pct}%` }}
              title={`Day ${d.day}: ${d.housing_used.toFixed(0)} cats${isOverflow ? ' (OVERFLOW)' : ''}`}
            />
          );
        })}
      </div>
      <div className="flex justify-between mt-1 text-[10px] text-zinc-400">
        {data.filter((_, i) => i % 10 === 0).map(d => (
          <span key={d.day}>{d.day}</span>
        ))}
      </div>
    </div>
  );
}
