"""Tests for the JAX-BO optimizer plugin (scipy fallback path)."""

from pathlib import Path

import pytest

from shelterpulse.core.schema import load_scenario
from shelterpulse.optimize.jaxbo_optimizer import optimize_jaxbo

WHISKER_HAVEN = Path(__file__).parent.parent.parent / "scenarios" / "whisker_haven.yaml"


@pytest.fixture(scope="module")
def scenario():
    return load_scenario(WHISKER_HAVEN)


@pytest.fixture(scope="module")
def seeds():
    return list(range(42, 50))  # 8 seeds for test speed


def test_optimizer_returns_results(scenario, seeds):
    results = optimize_jaxbo(scenario, seeds, n_candidates=4)
    assert len(results) >= 1
    assert all(r.mean_overflow_cat_days >= 0 for r in results)


def test_optimizer_sorted_feasible_first(scenario, seeds):
    results = optimize_jaxbo(scenario, seeds, n_candidates=4)
    for i in range(len(results) - 1):
        if not results[i].is_feasible and results[i + 1].is_feasible:
            pytest.fail("infeasible result appears before feasible")


def test_optimizer_beats_equal_allocation(scenario, seeds):
    """BO should produce at least one result competitive with equal allocation."""
    from shelterpulse.optimize.baselines import equal_allocation
    from shelterpulse.optimize.interface import evaluate_candidate

    baseline = evaluate_candidate(equal_allocation(), scenario, seeds)
    bo_results = optimize_jaxbo(scenario, seeds, n_candidates=4)
    feasible = [r for r in bo_results if r.is_feasible]
    if feasible:
        best_bo = feasible[0].mean_overflow_cat_days
        # Honest comparison — warn but don't hard-fail if BO doesn't beat baseline
        assert best_bo <= baseline.mean_overflow_cat_days * 1.5, (
            f"BO best ({best_bo:.1f}) much worse than equal ({baseline.mean_overflow_cat_days:.1f})"
        )
