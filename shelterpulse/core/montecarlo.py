"""Paired Monte Carlo with common random numbers (CRN).

CRN = same seed set used for all allocations, so difference in results
is attributable to the allocation, not noise.
"""

from __future__ import annotations

import dataclasses

import numpy as np

from shelterpulse.core.engine import run_simulation
from shelterpulse.core.schema import Scenario


@dataclasses.dataclass(frozen=True)
class MonteCarloSummary:
    mean_overflow: float
    std_overflow: float
    ci_95_lower: float
    ci_95_upper: float
    mean_cost: float
    n_replications: int


def run_paired(
    scenario: Scenario,
    seed_set: list[int],
) -> MonteCarloSummary:
    """Run scenario over seed_set, return summary statistics.

    Uses the provided seed_set directly (caller controls CRN — same seeds
    across all candidates ensures fair comparison).
    """
    overflow: list[float] = []
    costs: list[float] = []
    for seed in seed_set:
        r = run_simulation(scenario, seed=seed)
        overflow.append(float(r.overflow_cat_days))
        costs.append(r.total_cost)

    arr = np.array(overflow)
    n = len(arr)
    mean = float(arr.mean())
    std = float(arr.std(ddof=1)) if n > 1 else 0.0
    z = 1.96 if n >= 30 else 2.576
    margin = z * std / np.sqrt(n)
    return MonteCarloSummary(
        mean_overflow=mean,
        std_overflow=std,
        ci_95_lower=max(0.0, mean - margin),
        ci_95_upper=mean + margin,
        mean_cost=float(np.mean(costs)),
        n_replications=n,
    )


def make_seed_set(base_seed: int, n: int) -> list[int]:
    """Generate CRN seed set from a base seed."""
    return list(range(base_seed, base_seed + n))
