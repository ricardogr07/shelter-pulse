"""Optimizer interface — the single seam that all optimizers consume."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np

from shelterpulse.core.engine import run_simulation
from shelterpulse.core.schema import Scenario
from shelterpulse.optimize.workflow import CandidateAllocation, EvaluationResult


def evaluate_candidate(
    allocation: CandidateAllocation,
    scenario: Scenario,
    seed_set: Sequence[int],
) -> EvaluationResult:
    """Evaluate one candidate allocation over multiple replications.

    This is the single function every optimizer calls. Keeping it here means
    random, grid, heuristic, and JAX-BO all compare fairly under identical
    simulation budgets.

    Args:
        allocation: Budget fractions for the four intervention types.
        scenario: Validated scenario (immutable).
        seed_set: Replication seeds — use common random numbers for fair comparison.

    Returns:
        EvaluationResult with mean/std overflow cat-days and feasibility flag.
    """
    overflow_samples: list[float] = []
    cost_samples: list[float] = []

    for seed in seed_set:
        result = run_simulation(scenario, seed=seed)
        overflow_samples.append(float(result.overflow_cat_days))
        cost_samples.append(result.total_cost)

    mean_overflow = float(np.mean(overflow_samples))
    std_overflow = float(np.std(overflow_samples))
    mean_cost = float(np.mean(cost_samples))

    is_feasible = mean_cost <= scenario.total_intervention_budget * 1.05

    return EvaluationResult(
        allocation=allocation,
        mean_overflow_cat_days=mean_overflow,
        std_overflow_cat_days=std_overflow,
        mean_total_cost=mean_cost,
        is_feasible=is_feasible,
    )
