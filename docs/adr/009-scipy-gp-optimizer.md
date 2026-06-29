# ADR-009: Replace Fake BO with Real scipy GP+EI Optimizer

**Status:** Accepted | **Date:** 2026-06-26 | **Supersedes:** ADR-005 (partially)

## Context

ADR-005 accepted jaxbo as the BO plugin with "scipy fallback." In practice:
- `_jaxbo_optimize()` delegates to `_scipy_optimize()`: zero jaxbo code runs.
- `_scipy_optimize()` is random normal sampling evaluated independently: pure random search.
- The "Bayesian Optimization" label is dishonest; there is no surrogate model, no
  acquisition function, no sequential refinement.

This is a credibility risk for hackathon judging. The optimizer is the project's
central value proposition ("given limited budget, find the best allocation"). Random
search cannot credibly claim to outperform baselines in 30 evaluations.

## Decision

**Build a real GP+EI optimizer with two paths:**

1. **Primary (when jaxbo available):** Use `jaxbo` (pip install jaxbo, from
   https://github.com/ricardogr07/JAX-BO, Ricardo's fork, Apache-2.0). This uses
   jaxbo's `GP` model with RBF kernel + Expected Improvement acquisition, training
   hyperparameters via multi-start L-BFGS-B, and selecting next candidates via
   `compute_next_point_lbfgs()`.

2. **Fallback (no jaxbo/jax):** scipy-based GP+EI using numpy + scipy only. Hand-rolled
   RBF kernel, Cholesky factorization, MLE hyperparameters via scipy.optimize.minimize,
   EI acquisition with scipy.stats.norm.

Both paths:
- Use the same `evaluate_candidate()` interface
- Do real sequential Bayesian Optimization (not random search)
- Accept warm-start observations from baselines
- Operate on the 4-simplex (budget allocation space)

## Consequences

- `jaxbo>=0.1.2` added to `[project.optional-dependencies].optimize` (replaces raw jax/jaxlib)
- `scipy>=1.13` added to main dependencies
- The optimizer genuinely learns from past evaluations: judges can see convergence
- When jaxbo is not installed, falls back to scipy GP+EI (still real BO, not random)
- ~150 lines of GP+EI code in jaxbo_optimizer.py (scipy path)
- ADR-005 is superseded: jaxbo is now properly integrated via the real library API,
  not a fake delegation. The scipy path is a credible fallback, not a placeholder.
