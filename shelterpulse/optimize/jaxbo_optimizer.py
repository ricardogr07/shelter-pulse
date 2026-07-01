"""Bayesian Optimization optimizer plugin.

Primary: jaxbo (Ricardo's JAX-BO fork, Apache-2.0) — sequential GP+EI.
Fallback: random Dirichlet search if jaxbo/jax are unavailable.

Never calls run_simulation() directly — always via evaluate_candidate().
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import numpy as np

from shelterpulse.core.schema import Scenario
from shelterpulse.optimize.workflow import CandidateAllocation, EvaluationResult

try:
    import jax  # type: ignore[import-untyped]
    import jax.numpy as jnp  # type: ignore[import-untyped]
    from jaxbo import acquisitions, input_priors  # type: ignore[import-untyped]
    from jaxbo.models import GP  # type: ignore[import-untyped]
    _HAS_JAX = True
except ImportError:
    _HAS_JAX = False


# ── Simplex ↔ cube helpers ────────────────────────────────────────────────────
# Represent (a,b,c,d) summing to 1 as (a,b,c) in [0,1]^3; d = 1-a-b-c clamped ≥ 0.

def _to_cube(shares: np.ndarray) -> np.ndarray:
    """4-simplex point → 3-cube point (drop last coord)."""
    return shares[:3]


def _from_cube(x: np.ndarray) -> CandidateAllocation:
    """3-cube point → CandidateAllocation on 4-simplex via softmax normalization."""
    # softmax normalization keeps differentiability and handles out-of-simplex x
    d = np.append(x, 1.0 - x.sum())
    d = np.clip(d, 0.0, None)
    total = d.sum()
    if total < 1e-9:
        s = np.array([0.25, 0.25, 0.25, 0.25])
    else:
        s = d / total
    return CandidateAllocation(
        foster_support=float(s[0]),
        clinic_hours=float(s[1]),
        temporary_isolation=float(s[2]),
        adoption_events=float(s[3]),
    )


def _dirichlet_candidates(rng: np.random.Generator, n: int) -> np.ndarray:
    """n × 3 array of cube points sampled from Dirichlet(1,1,1,1)."""
    shares = rng.dirichlet([1.0, 1.0, 1.0, 1.0], size=n)
    return shares[:, :3]  # drop 4th coord


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
            results.append(r)

    # Fill up to n_init with random points if needed
    n_random = max(0, n_init - len(X_obs))
    if n_random > 0:
        for x in _dirichlet_candidates(rng, n_random):
            alloc = _from_cube(x)
            er = evaluate_candidate(alloc, scenario, seed_list)
            results.append(er)
            X_obs.append(x)
            done += 1
            if on_progress:
                on_progress(done, total)

    n_bo = n_candidates - (len(results) - (len(warm_start) if warm_start else 0))

    # --- Sequential GP+EI iterations ---
    lb = np.zeros(3)
    ub = np.ones(3)
    prior = input_priors.uniform_prior(lb=lb, ub=ub)  # type: ignore[arg-type]
    gp_options = {"kernel": "Matern52", "input_prior": prior}

    for _ in range(n_bo):
        X = np.array(X_obs)
        y_raw = np.array([r.mean_overflow_cat_days for r in results])

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
            c = jnp.array(cand).reshape(1, 3)
            mu, sigma = gp.predict(c, params=params, batch=batch, bounds=bounds)
            ei = float(acquisitions.EI(mu, sigma, best_y_norm)[0])
            ei_vals.append(ei)

        best_idx = int(np.argmin(ei_vals))  # EI returns negative
        x_next = candidates[best_idx]
        alloc = _from_cube(x_next)
        er = evaluate_candidate(alloc, scenario, seed_list)
        results.append(er)
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
    results: list[EvaluationResult] = list(warm_start) if warm_start else []

    n_needed = n_candidates - len(results)
    done = 0
    for x in _dirichlet_candidates(rng, max(0, n_needed)):
        results.append(evaluate_candidate(_from_cube(x), scenario, seed_list))
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
        return _jaxbo_gp_ei(scenario, seed_set, n_candidates, warm_start, on_progress=on_progress)
    return _random_search(scenario, seed_set, n_candidates, warm_start, on_progress=on_progress)
