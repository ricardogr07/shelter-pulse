# Shared Context: All Workers

Read this before starting any task. It applies to every worker (kiro, Codex, or any other agent).

## Project

**Name:** ShelterPulse  
**Root:** `c:/git/shelter-pulse`  
**Package:** `shelterpulse` (Python) + `ui/` (Next.js)  
**Deadline:** Jul 6 2026 (submit early); hard deadline Jul 7 23:59 BST  
**Jun 28 gate:** Run `run_optimization_sweep(scenario, budget=5000, n_candidates=4, use_bo=False)` → if sensible results → adopt Temporal; else drop it. See `.localagent/docs/10-temporal-gate.md`.

## Before you write any code

1. Read your worker file (`.localagent/agents/worker-*.md`) for scope, ownership, and done criteria
2. Read your spec file (`.localagent/docs/<number>-<name>.md`) for exact contracts
3. Read the relevant existing source files: understand what's already there before adding anything
4. Check `.localagent/docs/STATUS.md`: if your dependency tracks aren't DONE yet, stop

## Module boundary (critical)

`shelterpulse/core/` is a **pure Python library**: no I/O, no network, no imports from `shelterpulse.api`, `shelterpulse.cli`, or `shelterpulse.optimize`.

This is enforced by `tests/unit/test_no_cross_imports.py`. Violating it breaks CI.

## How to run code

```bash
# From c:/git/shelter-pulse:
uv run pytest tests/unit/<test_file>.py -v      # run specific test file
uv run pytest tests/unit/ -v                    # all unit tests
uv run pytest tests/unit/test_conservation.py  # conservation guard (always run after engine changes)
uv run shelterpulse --help                      # CLI smoke test
```

## How to mark yourself done

Edit `.localagent/docs/STATUS.md`. Find your track row and update:
- Status: `DONE`
- Tests: which pytest commands passed (copy the output line count)
- Notes: anything unusual or that the orchestrator should know

Format:
```
| Core-A | 02-interventions | kiro | DONE | test_interventions.py 8/8, test_conservation.py 4/4 | - |
```

## What you must NOT do

- `git commit`, `git push`, `git reset`, `git add` → orchestrator (Claude) only
- Edit `.github/workflows/` → orchestrator only
- Add packages to `pyproject.toml` or `ui/package.json` → ask first
- Edit files outside your ownership scope → see your worker file

## Coding style

- Minimum code that satisfies the spec (ponytail constraint)
- No comments that explain what the code does: only comments for non-obvious WHY
- Type annotations everywhere in Python (pyrefly checks this)
- `model_config = ConfigDict(frozen=True, extra="forbid")` on all new Pydantic models

## Quick reference: existing key functions

| Function | File | What it does |
|----------|------|-------------|
| `load_scenario(path)` | `core/schema.py` | Load + validate whisker_haven.yaml → `Scenario` |
| `run_simulation(scenario, seed, intervention=None)` | `core/engine.py` | One SimPy replication → `SimulationResult` |
| `evaluate_candidate(allocation, scenario, seed_set)` | `optimize/interface.py` | Multi-rep evaluation → `EvaluationResult` |
| `ALL_BASELINES` | `optimize/baselines.py` | Dict of named `CandidateAllocation` objects |
| `run_optimization_sweep(...)` | `optimize/workflow.py` | Full sweep → `list[EvaluationResult]` |
