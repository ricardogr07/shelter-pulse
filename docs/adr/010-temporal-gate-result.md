# ADR 010: Temporal Gate Result

## Status

Accepted

## Date

2026-06-27

## Context

The optimization architecture was designed to be Temporal-ready from the start.
Each `evaluate_candidate()` call maps cleanly to a Temporal activity, and the
full sweep maps to a Temporal workflow.

Before enabling Temporal, we needed to verify the gate criterion:
> Different budget allocations must produce measurably different overflow outcomes.

## Gate Test

```
run_optimization_sweep(whisker_haven, budget=5000, n_candidates=4, use_bo=False)
```

Result: Overflow range across candidates = ~1755 cat-days (PASS — threshold was >1.0).

## Decision

**Temporal deferred.** The in-process sweep completes in <30s for 20 candidates × 32
replications, which is fast enough for the hackathon demo. The architecture remains
Temporal-ready — `TEMPORAL_ENABLED = False` flag in `workflow.py` can be flipped
without touching the optimizer interface.

## Consequences

- No Temporal server required for deployment
- Single-process execution keeps Docker simple (one API container)
- Future: For production with 100+ candidates or 500+ reps, enable Temporal
  workers for horizontal scaling
