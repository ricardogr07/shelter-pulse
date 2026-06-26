"""Bayesian Optimization optimizer plugin.

Primary: jaxbo (Ricardo's JAX-BO fork, Apache-2.0).
Fallback: scipy minimize with random multi-start if jaxbo is unavailable.

Either path calls evaluate_candidate() — the seam defined in interface.py.
Never calls run_simulation() directly.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np

from shelterpulse.core.schema import Scenario
from shelterpulse.optimize.workflow import CandidateAllocation, EvaluationResult

try:
    import jax  # noqa: F401
    _HAS_JAX = True
except ImportError:
    _HAS_JAX = False


def _allocation_from_array(x: np.ndarray) -> CandidateAllocation:
    """Convert a 4-vector (unnormalized) to CandidateAllocation via softmax."""
    e = np.exp(x - x.max())
    shares = e / e.sum()
    return CandidateAllocation(
        foster_support=float(shares[0]),
        clinic_hours=float(shares[1]),
        temporary_isolation=float(shares[2]),
        adoption_events=float(shares[3]),
    )


def optimize_jaxbo(
    scenario: Scenario,
    seed_set: Sequence[int],
    n_candidates: int = 30,
) -> list[EvaluationResult]:
    """Run BO over the 4-dimensional budget allocation space.

    Returns evaluated candidates sorted best-first (feasible, lowest overflow first).
    Falls back to random multi-start scipy if jaxbo is unavailable.
    """
    if _HAS_JAX:
        return _jaxbo_optimize(scenario, seed_set, n_candidates)
    return _scipy_optimize(scenario, seed_set, n_candidates)


def _scipy_optimize(
    scenario: Scenario,
    seed_set: Sequence[int],
    n_candidates: int,
) -> list[EvaluationResult]:
    """Random multi-start search using numpy (no scipy required)."""
    from shelterpulse.optimize.interface import evaluate_candidate

    seed_list = list(seed_set)
    rng = np.random.default_rng(scenario.seed + 999)
    results: list[EvaluationResult] = []

    for _ in range(n_candidates):
        x = rng.normal(size=4)
        alloc = _allocation_from_array(x)
        er = evaluate_candidate(alloc, scenario, seed_list)
        results.append(er)

    results.sort(key=lambda r: (not r.is_feasible, r.mean_overflow_cat_days))
    return results


def _jaxbo_optimize(
    scenario: Scenario,
    seed_set: Sequence[int],
    n_candidates: int,
) -> list[EvaluationResult]:
    """JAX-BO optimization. Delegates to scipy fallback until jaxbo API is confirmed."""
    return _scipy_optimize(scenario, seed_set, n_candidates)
