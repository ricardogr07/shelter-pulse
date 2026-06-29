# ADR-005: Use jaxbo Fork as the Bayesian Optimizer Plugin

**Status:** Accepted | **Date:** 2026-06-26

## Context

The optimization problem (minimize expected overflow cat-days subject to budget and
workforce constraints by allocating a $5,000 budget across four intervention types) is a
low-dimensional, expensive-to-evaluate black-box optimization problem: exactly the regime
where Bayesian optimization with a Gaussian process surrogate outperforms grid/random search.

## Decision

Use the developer's own JAX-BO fork (`jaxbo`, v0.1.2, Apache-2.0) as the optimizer plugin.
It is wired behind the `evaluate_candidate()` interface defined in `optimize/interface.py`,
which every optimizer (random, grid, heuristic, jaxbo) consumes identically. This makes
the comparison honest: all baselines and jaxbo call the same simulation function with the
same seed sets.

## Consequences

- Authentic authored component: strengthens the Innovation category narrative.
- JAX dependency adds ~200 MB to the Docker image; acceptable for a demo deployment.
- On CPU-only CI runners, JAX runs in CPU mode (slower but correct).
- If jaxbo proves unstable on Windows/Docker during build, the fallback is the heuristic
  baseline, which runs with no additional dependencies.
