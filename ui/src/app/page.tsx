export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center bg-zinc-50 dark:bg-zinc-950 px-6">
      <div className="max-w-2xl w-full text-center space-y-6">
        <h1 className="text-5xl font-bold tracking-tight text-zinc-900 dark:text-zinc-50">
          ShelterPulse
        </h1>
        <p className="text-xl text-zinc-600 dark:text-zinc-400">
          Simulation &amp; optimization laboratory for cat shelter resource
          allocation
        </p>
        <p className="text-sm text-zinc-400 dark:text-zinc-600">
          UI coming in Phase 3 — core engine and API are being built first.
        </p>
      </div>
    </main>
  );
}
