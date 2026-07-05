# Module Boundaries

The core architectural constraint: `shelterpulse/core` is a pure library with no I/O.
All adapters (API, CLI, UI) call into it; it never imports from them.

![Module boundaries: five colored clusters (core in green, optimize in blue, queue in tan, store in purple, adapters in orange) showing each module's files and their dependency direction - core feeds optimize and the adapters directly, optimize feeds queue, queue feeds adapters, adapters feed store - with one dashed red arrow from core to adapters marked FORBIDDEN, enforced by tests/unit/test_no_cross_imports.py.](../images/module-boundaries.svg)

## Module map

| Path | Purpose |
|------|---------|
| `shelterpulse/core/` | Pure library: simulation engine, Monte Carlo, schema, interventions. Zero I/O. |
| `shelterpulse/optimize/` | Sweep orchestrator, Bayesian optimizer, baselines, evaluation interface |
| `shelterpulse/queue/` | Async job dispatch: queue abstraction, sync/RabbitMQ/SQS backends, worker, in-memory job store |
| `shelterpulse/store/` | Optional DuckDB persistence (run history, consent log, analytics). No-op stubs when the `store` extra isn't installed. |
| `shelterpulse/api/` | FastAPI REST adapter (thin I/O wrapper) |
| `shelterpulse/cli/` | Typer CLI adapter (thin I/O wrapper) |
| `ui/` | Next.js + React + TypeScript + Tailwind CSS frontend |
| `lambda/` | AWS Lambda worker for SQS-triggered BO sweeps. Calls `shelterpulse.store` directly (not through the API) since it already runs the optimization in-process. |

Note: `job_store.py` (SSE/status tracking for in-flight jobs, in-memory) and `store/duckdb_store.py` (durable run history on disk/EFS) are two different things despite the similar name — the former is ephemeral request-scoped state, the latter is persisted history.

## The key invariant

```
shelterpulse.core  imports from  nowhere in shelterpulse.*
```

Enforced by `tests/unit/test_no_cross_imports.py` which runs in CI on every PR.

This boundary is what makes the core usable from the API, CLI, and future adapters without circular imports. It also makes the core testable in isolation: no mock of FastAPI or Next.js needed to test the simulation engine.
