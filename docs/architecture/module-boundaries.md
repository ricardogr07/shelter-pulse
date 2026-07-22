# Module Boundaries

The core architectural constraint: `shelterpulse/core` is a pure library with no I/O.
All adapters (API, CLI, UI) call into it; it never imports from them.

![Module boundaries: five colored clusters (core in green, optimize in blue, queue in tan, store in purple, adapters in orange) showing each module's files and their dependency direction - core feeds optimize and the adapters directly, optimize feeds queue, queue feeds adapters, adapters feed store - with one dashed red arrow from core to adapters marked FORBIDDEN, enforced by tests/unit/test_no_cross_imports.py.](../images/module-boundaries.svg)

## Module map

| Path | Purpose |
|------|---------|
| `shelterpulse/core/` | Pure library: simulation engine, Monte Carlo, schema, interventions. Zero I/O. |
| `shelterpulse/optimize/` | Sweep orchestrator, Bayesian optimizer, baselines, evaluation interface |
| `shelterpulse/store/` | Optional DuckDB persistence (run history, consent log, analytics). No-op stubs when the `store` extra isn't installed. |
| `shelterpulse/api/` | FastAPI REST adapter (thin I/O wrapper); every endpoint synchronous |
| `shelterpulse/cli/` | Typer CLI adapter (thin I/O wrapper) |
| `ui/` | Next.js + React + TypeScript + Tailwind CSS frontend |

Note: `store/duckdb_store.py` holds durable run history on disk. (The in-memory `queue/job_store.py` it was once contrasted with was retired with the async workers in July 2026.)

## The key invariant

```
shelterpulse.core  imports from  nowhere in shelterpulse.*
```

Enforced by `tests/unit/test_no_cross_imports.py` which runs in CI on every PR.

This boundary is what makes the core usable from the API, CLI, and future adapters without circular imports. It also makes the core testable in isolation: no mock of FastAPI or Next.js needed to test the simulation engine.
