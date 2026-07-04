"""Optimization sweep orchestration for the in-process worker boundary."""

from __future__ import annotations

import dataclasses
from collections.abc import Sequence
from typing import Any

from shelterpulse.core.schema import Scenario

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
    is_feasible: bool   # True if allocated intervention spend is within budget
    # 95% confidence intervals (t-based)
    ci95_overflow_low: float = 0.0
    ci95_overflow_high: float = 0.0
    ci95_cost_low: float = 0.0
    ci95_cost_high: float = 0.0
    source: str = "candidate"


def _inprocess_sweep(
    scenario: Scenario,
    budget: float,
    n_candidates: int,
    seed_set: Sequence[int],
    on_progress: Any | None = None,
) -> list[EvaluationResult]:
    """Evaluate all baselines + n_candidates random allocations, return ranked results."""
    import numpy as np

    from shelterpulse.optimize.baselines import ALL_BASELINES
    from shelterpulse.optimize.interface import evaluate_candidate

    seed_list = list(seed_set)
    results: list[EvaluationResult] = []
    total = len(ALL_BASELINES) + n_candidates
    done = 0

    for name, alloc in ALL_BASELINES.items():
        results.append(dataclasses.replace(
            evaluate_candidate(alloc, scenario, seed_list),
            source=f"baseline:{name}",
        ))
        done += 1
        if on_progress:
            on_progress(done, total)

    # Random candidates (uniform Dirichlet -- guaranteed to sum to 1)
    rng = np.random.default_rng(scenario.seed)
    for _ in range(n_candidates):
        shares = rng.dirichlet([1.0, 1.0, 1.0, 1.0])
        alloc = CandidateAllocation(
            foster_support=float(shares[0]),
            clinic_hours=float(shares[1]),
            temporary_isolation=float(shares[2]),
            adoption_events=float(shares[3]),
        )
        results.append(dataclasses.replace(
            evaluate_candidate(alloc, scenario, seed_list),
            source="random",
        ))
        done += 1
        if on_progress:
            on_progress(done, total)

    results.sort(key=lambda r: (not r.is_feasible, r.mean_overflow_cat_days))
    return results


def run_optimization_sweep(
    scenario: Scenario,
    budget: float,
    n_candidates: int = 30,
    seed_set: Sequence[int] | None = None,
    use_bo: bool = True,
    on_progress: Any | None = None,
) -> list[EvaluationResult]:
    """Entry point for the optimization sweep.

    Args:
        scenario: Validated scenario.
        budget: Total intervention budget in USD.
        n_candidates: Number of candidate allocations to evaluate.
        seed_set: Replication seeds. Defaults to 64 seeds starting from scenario.seed.
        use_bo: If True, run JAX-BO (or deterministic random fallback) merged with baselines.
        on_progress: Optional callback(done: int, total: int) called after each
            candidate evaluation. Used by workers to report progress.

    Returns:
        List of EvaluationResult, one per candidate evaluated.
    """
    if seed_set is None:
        seed_set = list(range(scenario.seed, scenario.seed + scenario.n_replications))

    if use_bo:
        from shelterpulse.optimize.jaxbo_optimizer import optimize_jaxbo
        from shelterpulse.optimize.baselines import ALL_BASELINES

        # Unified progress: BO candidates + baselines
        total = n_candidates + len(ALL_BASELINES)
        _counter = [0]  # mutable closure

        def _unified_progress(done: int, total_inner: int) -> None:
            _counter[0] += 1
            if on_progress:
                on_progress(_counter[0], total)

        baseline_results = _inprocess_sweep(scenario, budget, 0, seed_set, on_progress=_unified_progress)
        bo_results = optimize_jaxbo(
            scenario,
            seed_set,
            n_candidates,
            warm_start=baseline_results,
            on_progress=_unified_progress,
        )
        combined = baseline_results + bo_results
        combined.sort(key=lambda r: (not r.is_feasible, r.mean_overflow_cat_days))
        return combined
    return _inprocess_sweep(scenario, budget, n_candidates, seed_set, on_progress=on_progress)
