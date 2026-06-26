"""Optimization sweep orchestration.

TEMPORAL_ENABLED = False until the Jun 28 gate check.
Flip this flag (and enable the docker-compose temporal profile) once the core
simulation is running end-to-end on a trusted baseline.
"""

from __future__ import annotations

import dataclasses
from collections.abc import Sequence
from typing import Any

from shelterpulse.core.schema import Scenario

TEMPORAL_ENABLED = False


@dataclasses.dataclass(frozen=True)
class CandidateAllocation:
    """Budget allocation across the four intervention types (fractions summing to ≤ 1)."""

    foster_support: float
    clinic_hours: float
    temporary_isolation: float
    adoption_events: float

    def __post_init__(self) -> None:
        total = self.foster_support + self.clinic_hours + self.temporary_isolation + self.adoption_events
        if total > 1.0 + 1e-6:
            raise ValueError(f"Allocation shares sum to {total:.4f}, must be ≤ 1.0")


@dataclasses.dataclass(frozen=True)
class EvaluationResult:
    """Outcome of evaluating one candidate allocation over multiple replications."""

    allocation: CandidateAllocation
    mean_overflow_cat_days: float
    std_overflow_cat_days: float
    mean_total_cost: float
    is_feasible: bool   # True if mean_total_cost ≤ scenario budget


def _inprocess_sweep(
    scenario: Scenario,
    budget: float,
    n_candidates: int,
    seed_set: Sequence[int],
) -> list[EvaluationResult]:
    """Evaluate all baselines + n_candidates random allocations, return ranked results."""
    import numpy as np

    from shelterpulse.optimize.baselines import ALL_BASELINES
    from shelterpulse.optimize.interface import evaluate_candidate

    seed_list = list(seed_set)
    results: list[EvaluationResult] = []

    for _name, alloc in ALL_BASELINES.items():
        results.append(evaluate_candidate(alloc, scenario, seed_list))

    # Random candidates (uniform Dirichlet — guaranteed to sum to 1)
    rng = np.random.default_rng(scenario.seed)
    for _ in range(n_candidates):
        shares = rng.dirichlet([1.0, 1.0, 1.0, 1.0])
        alloc = CandidateAllocation(
            foster_support=float(shares[0]),
            clinic_hours=float(shares[1]),
            temporary_isolation=float(shares[2]),
            adoption_events=float(shares[3]),
        )
        results.append(evaluate_candidate(alloc, scenario, seed_list))

    results.sort(key=lambda r: (not r.is_feasible, r.mean_overflow_cat_days))
    return results


def _temporal_sweep(
    scenario: Scenario,
    budget: float,
    n_candidates: int,
    seed_set: Sequence[int],
) -> list[EvaluationResult]:
    """Run the optimization sweep via Temporal durable workflows.

    Wired in after the Jun 28 gate check passes.
    Each candidate evaluation becomes a Temporal activity;
    the full sweep is a durable, resumable workflow.
    """
    raise NotImplementedError(
        "Temporal sweep not yet implemented — set TEMPORAL_ENABLED = False "
        "until workflow.py is wired to a running Temporal server."
    )


def run_optimization_sweep(
    scenario: Scenario,
    budget: float,
    n_candidates: int = 30,
    seed_set: Sequence[int] | None = None,
    use_bo: bool = True,
) -> list[EvaluationResult]:
    """Entry point for the optimization sweep.

    Args:
        scenario: Validated scenario.
        budget: Total intervention budget in USD.
        n_candidates: Number of candidate allocations to evaluate.
        seed_set: Replication seeds. Defaults to 64 seeds starting from scenario.seed.
        use_bo: If True, run JAX-BO optimizer (or scipy fallback) merged with baselines.

    Returns:
        List of EvaluationResult, one per candidate evaluated.
    """
    if seed_set is None:
        seed_set = list(range(scenario.seed, scenario.seed + scenario.n_replications))

    if TEMPORAL_ENABLED:
        return _temporal_sweep(scenario, budget, n_candidates, seed_set)
    if use_bo:
        from shelterpulse.optimize.jaxbo_optimizer import optimize_jaxbo

        bo_results = optimize_jaxbo(scenario, seed_set, n_candidates)
        baseline_results = _inprocess_sweep(scenario, budget, 0, seed_set)
        combined = baseline_results + bo_results
        combined.sort(key=lambda r: (not r.is_feasible, r.mean_overflow_cat_days))
        return combined
    return _inprocess_sweep(scenario, budget, n_candidates, seed_set)
