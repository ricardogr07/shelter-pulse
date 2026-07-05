"""Bayesian Optimization optimizer plugin.

Primary: jaxbo (Ricardo's JAX-BO fork, Apache-2.0) — sequential GP+EI.
Fallback: random Dirichlet search if jaxbo/jax are unavailable.

Never calls run_simulation() directly — always via evaluate_candidate().
"""

from __future__ import annotations

import dataclasses
import logging
from collections.abc import Sequence
from typing import Any

import numpy as np

from shelterpulse.core.schema import Scenario
from shelterpulse.optimize.workflow import CandidateAllocation, EvaluationResult

logger = logging.getLogger(__name__)

try:
    import jax  # type: ignore[import-untyped]
    import jax.numpy as jnp  # type: ignore[import-untyped]
    from jaxbo import acquisitions, input_priors  # type: ignore[import-untyped]
    from jaxbo.models import GP  # type: ignore[import-untyped]
    _HAS_JAX = True
    logger.info("jax/jaxbo import succeeded - real GP+EI optimization available")
except ImportError as exc:
    _HAS_JAX = False
    logger.warning("jax/jaxbo import failed, using random-search fallback: %s", exc)


# ── Simplex helpers ───────────────────────────────────────────────────────────
# Candidate proposals use the full available budget (four shares summing to
# one). Warm-start observations may include the zero-intervention baseline.

def _to_cube(shares: np.ndarray) -> np.ndarray:
    """Return the four explicit spending coordinates used by the GP."""
    return shares[:4]


def _from_cube(x: np.ndarray) -> CandidateAllocation:
    """Project four coordinates onto the budget simplex when necessary."""
    s = np.clip(np.asarray(x, dtype=float), 0.0, 1.0)
    total = float(s.sum())
    if total > 1.0:
        s = s / total
    return CandidateAllocation(
        foster_support=float(s[0]),
        clinic_hours=float(s[1]),
        temporary_isolation=float(s[2]),
        adoption_events=float(s[3]),
    )


def _dirichlet_candidates(rng: np.random.Generator, n: int) -> np.ndarray:
    """Sample full-budget allocations on the four-share simplex."""
    return rng.dirichlet([1.0, 1.0, 1.0, 1.0], size=n)


# ── jaxbo GP+EI path ──────────────────────────────────────────────────────────

def _jaxbo_gp_ei(
    scenario: Scenario,
    seed_set: Sequence[int],
    n_candidates: int,
    warm_start: list[EvaluationResult] | None,
    on_progress: Any | None = None,
) -> list[EvaluationResult]:
    """Sequential GP+EI loop using jaxbo.models.GP and jaxbo.acquisitions.EI."""
    from shelterpulse.optimize.interface import evaluate_candidate

    seed_list = list(seed_set)
    rng = np.random.default_rng(scenario.seed + 7)
    n_init = max(5, min(8, n_candidates // 3))

    # --- Initialise with warm-start points or random Dirichlet samples ---
    observations: list[EvaluationResult] = list(warm_start or [])
    results: list[EvaluationResult] = []
    X_obs: list[np.ndarray] = []
    done = 0
    total = n_candidates

    if warm_start:
        for r in warm_start:
            cube_x = _to_cube(np.array([
                r.allocation.foster_support,
                r.allocation.clinic_hours,
                r.allocation.temporary_isolation,
                r.allocation.adoption_events,
            ]))
            X_obs.append(cube_x)

    # Fill up to n_init with random points if needed
    n_random = min(n_candidates, max(0, n_init - len(X_obs)))
    if n_random > 0:
        for x in _dirichlet_candidates(rng, n_random):
            alloc = _from_cube(x)
            er = dataclasses.replace(
                evaluate_candidate(alloc, scenario, seed_list),
                source="bo",
            )
            results.append(er)
            observations.append(er)
            X_obs.append(x)
            done += 1
            if on_progress:
                on_progress(done, total)

    n_bo = n_candidates - len(results)

    # --- Sequential GP+EI iterations ---
    lb = np.zeros(4)
    ub = np.ones(4)
    prior = input_priors.uniform_prior(lb=lb, ub=ub)  # type: ignore[arg-type]
    gp_options = {"kernel": "Matern52", "input_prior": prior}

    for _ in range(n_bo):
        X = np.array(X_obs)
        y_raw = np.array([r.mean_overflow_cat_days for r in observations])

        # Normalise y for GP stability
        y_mean, y_std = y_raw.mean(), y_raw.std() + 1e-8
        y_norm = ((y_raw - y_mean) / y_std).reshape(-1, 1)

        # Normalise X to [0,1]^3 (already in cube but clamp for safety)
        X_norm = np.clip(X, 0.0, 1.0)

        batch = {"X": X_norm, "y": y_norm}
        bounds = {"lb": lb, "ub": ub}

        gp = GP(gp_options)
        rng_key = jax.random.PRNGKey(int(rng.integers(1 << 31)))
        params = gp.train(batch, rng_key, num_restarts=3)

        best_y_norm = float(y_norm.min())

        # Maximise EI over a grid of Dirichlet candidates
        candidates = _dirichlet_candidates(rng, 256)
        ei_vals = []
        for cand in candidates:
            c = jnp.array(cand).reshape(1, 4)
            mu, sigma = gp.predict(c, params=params, batch=batch, bounds=bounds)
            ei = float(acquisitions.EI(mu, sigma, best_y_norm)[0])
            ei_vals.append(ei)

        best_idx = int(np.argmin(ei_vals))  # EI returns negative
        x_next = candidates[best_idx]
        alloc = _from_cube(x_next)
        er = dataclasses.replace(
            evaluate_candidate(alloc, scenario, seed_list),
            source="bo",
        )
        results.append(er)
        observations.append(er)
        X_obs.append(x_next)
        done += 1
        if on_progress:
            on_progress(done, total)

    results.sort(key=lambda r: (not r.is_feasible, r.mean_overflow_cat_days))
    return results


# ── Random fallback ───────────────────────────────────────────────────────────

def _random_search(
    scenario: Scenario,
    seed_set: Sequence[int],
    n_candidates: int,
    warm_start: list[EvaluationResult] | None,
    on_progress: Any | None = None,
) -> list[EvaluationResult]:
    from shelterpulse.optimize.interface import evaluate_candidate

    seed_list = list(seed_set)
    rng = np.random.default_rng(scenario.seed + 999)
    results: list[EvaluationResult] = []
    done = 0
    for x in _dirichlet_candidates(rng, n_candidates):
        results.append(dataclasses.replace(
            evaluate_candidate(_from_cube(x), scenario, seed_list),
            source="random",
        ))
        done += 1
        if on_progress:
            on_progress(done, n_candidates)

    results.sort(key=lambda r: (not r.is_feasible, r.mean_overflow_cat_days))
    return results


# ── Public entry point ────────────────────────────────────────────────────────

def optimize_jaxbo(
    scenario: Scenario,
    seed_set: Sequence[int],
    n_candidates: int = 30,
    warm_start: list[EvaluationResult] | None = None,
    on_progress: Any | None = None,
) -> list[EvaluationResult]:
    """Run BO over the 4-dimensional budget allocation space.

    Returns candidates sorted best-first (feasible, lowest overflow first).
    Uses jaxbo GP+EI when jax is available, random Dirichlet search otherwise.

    Args:
        on_progress: Optional callback(done: int, total: int) called after each
            candidate evaluation.
    """
    if _HAS_JAX:
        logger.info("optimize_jaxbo: using GP+EI (n_candidates=%d)", n_candidates)
        return _jaxbo_gp_ei(scenario, seed_set, n_candidates, warm_start, on_progress=on_progress)
    logger.info("optimize_jaxbo: using random-search fallback (n_candidates=%d)", n_candidates)
    return _random_search(scenario, seed_set, n_candidates, warm_start, on_progress=on_progress)
