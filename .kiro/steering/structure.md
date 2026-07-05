---
inclusion: always
---

# ShelterPulse: Project Structure & Module Boundaries

## Package layout

```
c:/git/shelter-pulse/
├── shelterpulse/              ← Python package
│   ├── core/                  ← PURE library (no I/O, no network, no file access)
│   │   ├── schema.py          ← Pydantic v2 models + YAML loader (load_scenario)
│   │   ├── engine.py          ← SimPy discrete-event simulation (run_simulation)
│   │   ├── interventions.py   ← Dollar→resource adapters (InterventionParams, resolve_intervention)
│   │   ├── montecarlo.py      ← Paired CRN Monte Carlo (run_paired, make_seed_set)
│   │   └── export.py          ← YAML + CSV export (export_results)
│   ├── optimize/
│   │   ├── interface.py       ← evaluate_candidate(): THE seam all optimizers call
│   │   ├── baselines.py       ← Named baselines (ALL_BASELINES dict)
│   │   ├── jaxbo_optimizer.py ← BO plugin (jaxbo primary, scipy fallback)
│   │   └── workflow.py        ← run_optimization_sweep()
│   ├── store/
│   │   └── duckdb_store.py    ← Optional DuckDB persistence: save_run(), load_run()
│   ├── queue/                 ← Async job dispatch (see architecture.md for backends)
│   ├── api/
│   │   └── app.py             ← FastAPI: /health /simulate /optimize /baselines /export
│   └── cli/
│       └── main.py            ← Typer: simulate, optimize, baselines, export
├── lambda/
│   └── handler.py             ← SQS event handler: production async worker
├── ui/                        ← Next.js app, i18n-routed under [lang] (en/es)
│   ├── src/app/[lang]/page.tsx           ← Landing page (hero + CTAs)
│   ├── src/app/[lang]/demo/page.tsx      ← Guided Whisker Haven wizard
│   ├── src/app/[lang]/how-it-works/page.tsx ← Model walkthrough + whitepaper download
│   ├── src/app/[lang]/simulate/page.tsx  ← Custom simulation builder
│   ├── src/components/        ← Shared components (NavBar, Footer, charts)
│   ├── src/i18n/dictionaries.ts ← All UI copy, en/es - edit here, not inline
│   ├── src/api.ts             ← fetch wrappers for backend
│   ├── src/types.ts           ← TypeScript types
│   └── AGENTS.md              ← MUST READ before writing Next.js code
├── scenarios/
│   └── whisker_haven.yaml     ← The primary demo scenario
├── tests/
│   ├── unit/                  ← pytest unit tests
│   └── e2e/                   ← pytest e2e (API) + Cypress (UI)
└── .kiro/
    ├── steering/               ← Always-loaded agent context (this file + others)
    ├── agents/                 ← Role definitions: PLANNER, ORCHESTRATOR, DIRECTOR, worker-*.md
    ├── docs/                   ← Reusable playbooks (issue workflow, local dev, PR/CI-CD)
    └── README.md                ← Kiro Track submission write-up
```

## The critical invariant

```
shelterpulse.core  imports from  nowhere in shelterpulse.*
```

`shelterpulse/core/` is a pure Python library. It has no I/O, no network calls, no file access (except the YAML loader in `schema.py` which is the entry point). All adapters call into core; core never imports from `api/`, `cli/`, `optimize/`, or `ui/`.

**This is enforced by CI:** `tests/unit/test_no_cross_imports.py` fails the build if violated.

## Dependency arrows

```
shelterpulse/core  ←── shelterpulse/optimize  ←── api/app.py
                                               ←── cli/main.py
api/app.py  ←── ui/ (HTTP/JSON, not Python imports)
```

## Forbidden patterns

- `core/engine.py` must NEVER import from `optimize/`
- `core/*.py` must NEVER import from `api/` or `cli/`
- `api/app.py` must NEVER contain simulation logic: call core functions
- `cli/main.py` must NEVER contain simulation logic: call core functions
- `ui/` communicates with backend via HTTP only: no Python imports

## File ownership per worker

Each `worker-*.md` file in `.kiro/agents/` lists exactly which files that worker owns and which are forbidden. Workers must not touch files outside their ownership scope.
