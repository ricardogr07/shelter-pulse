export default function CIBadge({ low, high }: { low: number; high: number; mean: number }) {
  const margin = ((high - low) / 2).toFixed(1);
  return (
    <span
      className="text-xs text-zinc-500 dark:text-zinc-400 ml-1"
      title={`95% CI: [${low.toFixed(1)}, ${high.toFixed(1)}]`}
    >
      ±{margin}
    </span>
  );
}
