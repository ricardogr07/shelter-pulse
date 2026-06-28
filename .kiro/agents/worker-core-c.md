# Worker: Core-C — JAX-BO Optimizer Plugin

**Model:** Claude Opus 4.6 | **Effort:** high  
**Depends on:** Core-A + Core-B must be DONE first

## Role

Wire the JAX-BO optimizer (Ricardo's `jaxbo` fork) as a plugin behind `evaluate_candidate()`. Include a scipy fallback so it works even if `jax` isn't installed. Update `run_optimization_sweep` to use it when `use_bo=True`.

## Read first

```
@.localagent/agents/SHARED.md
@.localagent/docs/04-jaxbo.md
```

## Files you own

| File | Action |
|------|--------|
| `shelterpulse/optimize/jaxbo_optimizer.py` | **Create** |
| `shelterpulse/optimize/workflow.py` | **Modify** — add `use_bo: bool = True` to `run_optimization_sweep` only |
| `tests/unit/test_jaxbo.py` | **Create** |

## Files you must NOT touch

- `optimize/interface.py` — the seam; never modify it
- `optimize/baselines.py` — never modify
- `core/*.py` — not your scope
- `api/`, `cli/`, `ui/` — not your scope

## Done criteria

- [ ] `uv run pytest tests/unit/test_jaxbo.py -v` — all tests pass **without** `jax` installed (scipy fallback path)
- [ ] `uv run pytest tests/unit/test_conservation.py -v` — still passes
- [ ] `run_optimization_sweep(scenario, budget=5000, n_candidates=4, use_bo=True)` returns results
- [ ] Update `.localagent/docs/STATUS.md` row for Core-C

## Key contracts

- `optimize_jaxbo(scenario, seed_set, n_candidates)` → `list[EvaluationResult]`
- Must call `evaluate_candidate()` — never `run_simulation()` directly
- `_allocation_from_array(x)` — 4-vector → `CandidateAllocation` via softmax (shares always sum to 1)
- scipy fallback: `scipy.optimize.minimize` with Nelder-Mead, multi-start random init
- jax path: attempt `import jax`; if `ImportError`, fall back silently
- `jax`/`jaxlib` stay in `[project.optional-dependencies].optimize` — never add to main deps
- Results sorted: feasible first, then ascending overflow
