# Shared -- Context for ALL Workers

Read this before writing a single line of code.

## Project

ShelterPulse -- simulation + optimization lab for cat-shelter resource allocation.
Originally built for #hackthekitty 2026. Public repo: ricardogr07/shelter-pulse.

Root: `c:/git/shelter-pulse`
Python package: `shelterpulse`
UI: `ui/` (Next.js + TypeScript + Tailwind)
Scenarios: `scenarios/` (Whisker Haven is the primary demo scenario; archetype variants also live here)

## Before Any Code

1. Check the relevant GitHub issue, if one exists: `gh issue view <N> --repo ricardogr07/shelter-pulse`
2. Read your worker file (`.kiro/agents/worker-<domain>.md`)
3. Read the relevant source files before touching them
4. Check `.kiro/steering/` files (architecture, tech, rules -- always included by kiro)

## Module Boundary -- CRITICAL

`shelterpulse/core/` is a pure Python library. Zero I/O, zero network, zero imports from:
- `shelterpulse.api`
- `shelterpulse.cli`

CI-enforced by `tests/unit/test_no_cross_imports.py`. As a design convention (not yet
CI-enforced), core also should not import from `shelterpulse.optimize`.

Dependency arrows:
```
core  <--  optimize  <--  api/app.py  <--  ui/ (HTTP/JSON only, no Python import)
core  <--  optimize  <--  cli/main.py
```

## Current API Endpoints (all exist in shelterpulse/api/app.py)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| /health | GET | Health check |
| /simulate | POST | Single simulation run |
| /optimize | POST | Full optimization sweep |
| /baselines | GET | 5 named baseline allocations |
| /sensitivity | POST | Tornado chart data |
| /simulate/timeline | POST | Daily snapshot timeline |
| /simulate/builder | POST | Custom scenario simulation |
| /optimize/builder | POST | Custom scenario optimization |
| /export | POST | Download YAML+CSV results |

## Key Functions

| Function | File | Purpose |
|----------|------|---------|
| `load_scenario()` | core/schema.py | Load a scenario YAML → Scenario |
| `run_simulation(scenario, seed, intervention)` | core/engine.py | One SimPy replication |
| `resolve_intervention(scenario, allocation)` | core/interventions.py | Budget → InterventionParams |
| `run_paired(scenario, intervention, seed_set)` | core/montecarlo.py | CRN paired replications |
| `evaluate_candidate(allocation, scenario, seed_set)` | optimize/interface.py | THE evaluation seam |
| `run_optimization_sweep(scenario, budget, ...)` | optimize/workflow.py | Full sweep → ranked list |

## CRN Discipline

All optimization candidates must use the **same seed_set**. Common Random Numbers removes
replication variance from comparisons. The seed_set is fixed at sweep start in workflow.py
and passed to every `evaluate_candidate()` call. Do NOT call `run_simulation()` directly
from an optimizer -- always go through `evaluate_candidate()`.

## Frozen Scenario

`Scenario` has `model_config = ConfigDict(frozen=True)`. Never add mutable state.
If a scenario change is needed mid-sweep, create a new `Scenario` object.

## Coding Style

- Minimum code (ponytail). YAGNI. No premature abstractions.
- Type annotations on every function signature.
- `model_config = ConfigDict(frozen=True, extra="forbid")` on Pydantic models.
- No `any` in TypeScript without comment justification.
- Domain language: cats, kittens, isolation queue, foster placement, vet tech, adoption counselor.
  NEVER: "entities", "units", "agents" (unless AI agent context).

## Forbidden for ALL Workers

- `git add/commit/push/reset/amend` (Orchestrator only)
- Edit `.github/workflows/` (Director approval required)
- `pip install` or `npm install <new-package>` modifying lock files (Orchestrator approval)
- `terraform destroy` (Director approval required)
- Edit files outside your worker's ownership zone (see your worker-*.md)
- Mark done without running the required tests first
