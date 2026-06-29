# Worker: Core-B: Monte Carlo Runner

**Model:** Claude Sonnet 4.6 | **Effort:** high  
**Depends on:** Core-A must be DONE first (engine must accept `intervention=` param)

## Role

Implement the paired Monte Carlo runner with common random numbers (CRN), and replace the placeholder `_inprocess_sweep` in `workflow.py` with a real multi-candidate sweep.

## Read first

```
@.localagent/agents/SHARED.md
@.localagent/docs/03-montecarlo.md
```

## Files you own

| File | Action |
|------|--------|
| `shelterpulse/core/montecarlo.py` | **Create** |
| `shelterpulse/optimize/workflow.py` | **Modify**: replace `_inprocess_sweep` body only |
| `tests/unit/test_montecarlo.py` | **Create** |

## Files you must NOT touch

- `core/engine.py`: owned by Core-A
- `core/interventions.py`: owned by Core-A
- `optimize/interface.py`: owned by Core-A
- `optimize/baselines.py`: never modify
- `optimize/jaxbo_optimizer.py`: owned by Core-C
- `api/`, `cli/`, `ui/`: not your scope

## Done criteria

- [ ] `uv run pytest tests/unit/test_montecarlo.py -v`: all tests pass
- [ ] `uv run pytest tests/unit/test_conservation.py -v`: still passes
- [ ] `run_optimization_sweep(scenario, budget=5000, n_candidates=4, use_bo=False)` returns at least 4 results with varying overflow values
- [ ] Results are sorted: feasible first, then by ascending `mean_overflow_cat_days`
- [ ] Update `.localagent/docs/STATUS.md` row for Core-B

## Key contracts from the spec

- `make_seed_set(base_seed, n)` → `list[int]`: deterministic CRN seed generation
- `run_paired(scenario, intervention, seed_set)` → `MonteCarloSummary`: one allocation evaluated
- `_inprocess_sweep` must evaluate `ALL_BASELINES` + `n_candidates` random Dirichlet allocations
- Sort order: feasible first, then by `mean_overflow_cat_days` ascending
- `TEMPORAL_ENABLED` flag and `_temporal_sweep` stub must remain untouched
