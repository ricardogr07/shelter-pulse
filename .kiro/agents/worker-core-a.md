# Worker: Core-A — Intervention Adapters

**Model:** Claude Opus 4.6 | **Effort:** high  
**Priority:** CRITICAL — Jun 28 gate blocker. Do this first.

## Role

Wire the four intervention types into the SimPy engine so that comparing allocations produces different simulation outputs. Right now `engine.py` ignores interventions completely.

## Read first

```
@.localagent/agents/SHARED.md
@.localagent/docs/02-interventions.md
```

The spec in `02-interventions.md` contains exact function signatures, constants, test cases, and guard rails. Follow it precisely.

## Files you own

| File | Action |
|------|--------|
| `shelterpulse/core/interventions.py` | **Create** |
| `shelterpulse/core/engine.py` | **Modify** — add `intervention: InterventionParams \| None = None` parameter only |
| `shelterpulse/optimize/interface.py` | **Modify** — call `resolve_intervention()` before `run_simulation()` |
| `tests/unit/test_interventions.py` | **Create** |

## Files you must NOT touch

- `core/schema.py` — `InterventionDef` stays as-is
- `core/montecarlo.py` — not your file
- `optimize/workflow.py` — not your file  
- `optimize/baselines.py` — not your file
- `api/`, `cli/`, `ui/` — not your scope
- `.github/workflows/` — never

## Done criteria

- [ ] `uv run pytest tests/unit/test_interventions.py -v` — all tests pass
- [ ] `uv run pytest tests/unit/test_conservation.py -v` — still passes (no regression)
- [ ] `uv run pytest tests/unit/test_no_cross_imports.py -v` — still passes
- [ ] `evaluate_candidate(zero_allocation(), scenario, [42])` and `evaluate_candidate(equal_allocation(), scenario, [42])` produce **different** `mean_overflow_cat_days` (the core requirement)
- [ ] Update `.localagent/docs/STATUS.md` row for Core-A

## Quick sanity check

After implementation, run this to verify interventions are wired:

```bash
uv run python -c "
from shelterpulse.core.schema import load_scenario
from shelterpulse.optimize.baselines import zero_allocation, equal_allocation
from shelterpulse.optimize.interface import evaluate_candidate
from pathlib import Path

s = load_scenario(Path('scenarios/whisker_haven.yaml'))
seeds = [42, 43, 44, 45]
z = evaluate_candidate(zero_allocation(), s, seeds)
e = evaluate_candidate(equal_allocation(), s, seeds)
print(f'zero overflow:  {z.mean_overflow_cat_days:.1f}')
print(f'equal overflow: {e.mean_overflow_cat_days:.1f}')
print('WIRED OK' if abs(z.mean_overflow_cat_days - e.mean_overflow_cat_days) > 0.01 else 'NOT WIRED — interventions have no effect')
"
```
