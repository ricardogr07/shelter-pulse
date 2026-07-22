import { STATIC_MODE } from "@/api";

/**
 * Shown only when NEXT_PUBLIC_STATIC_MODE=1. Tells visitors the page is a free
 * static showcase replaying a recorded sweep, and points them at the repo for
 * live compute. Renders nothing in the normal (backed) build.
 */
export function StaticModeBanner() {
  if (!STATIC_MODE) return null;
  return (
    <div className="mb-6 rounded-lg border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-900 dark:border-amber-700 dark:bg-amber-950 dark:text-amber-200">
      <strong>Static showcase.</strong> Live compute is paused to keep this page
      free to host. The optimizer results below replay a recorded Whisker Haven
      sweep. For live simulation and custom scenarios, clone the repo and run{" "}
      <code className="rounded bg-amber-100 px-1 dark:bg-amber-900">docker-compose up</code>.
    </div>
  );
}
