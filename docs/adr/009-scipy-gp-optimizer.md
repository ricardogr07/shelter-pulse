# ADR-009: Use real GP+EI with an explicitly labeled random fallback

**Status:** Amended | **Date:** 2026-06-26 | **Amended:** 2026-07-02

## Context

Earlier optimizer code and documentation described random sampling as Bayesian optimization and proposed an unimplemented scipy GP fallback. Both descriptions were misleading.

## Decision

1. When JAX and `jaxbo` are available, use a sequential Gaussian-process path with a Matérn-5/2 kernel and Expected Improvement.
2. Warm-start the GP with all five named baseline observations.
3. At each iteration, score 256 feasible Dirichlet proposals and evaluate the best acquisition value.
4. Keep all four spending shares in the GP representation so zero intervention and all-in-events are distinct.
5. When JAX/`jaxbo` is unavailable, run deterministic seeded Dirichlet random search and label those results `random`. Do not call the fallback BO.

All paths use `evaluate_candidate()` and the same paired seed/stream contract.

## Consequences

- `n_candidates` counts newly evaluated candidates; warm-start baselines are retained separately and are not duplicated.
- A named baseline can rank above every BO candidate.
- The fallback is operationally simpler but provides no GP surrogate or acquisition optimization.
- A future scipy GP path requires a separate implementation and validation decision; it is not current behavior.
