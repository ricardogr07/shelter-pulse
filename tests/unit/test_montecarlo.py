from pathlib import Path

import pytest

from shelterpulse.core.montecarlo import make_seed_set, run_paired
from shelterpulse.core.schema import load_scenario

WHISKER_HAVEN = Path(__file__).parent.parent.parent / "scenarios" / "whisker_haven.yaml"


@pytest.fixture(scope="module")
def scenario():
    return load_scenario(WHISKER_HAVEN)


def test_summary_has_positive_values(scenario):
    seeds = make_seed_set(42, 8)
    summary = run_paired(scenario, seeds)
    assert summary.mean_overflow >= 0
    assert summary.ci_95_lower <= summary.mean_overflow <= summary.ci_95_upper
    assert summary.n_replications == 8


def test_crn_reproducible(scenario):
    seeds = make_seed_set(42, 8)
    s1 = run_paired(scenario, seeds)
    s2 = run_paired(scenario, seeds)
    assert s1.mean_overflow == s2.mean_overflow


def test_make_seed_set():
    seeds = make_seed_set(100, 5)
    assert seeds == [100, 101, 102, 103, 104]


def test_sweep_returns_sorted_results(scenario):
    from shelterpulse.optimize.workflow import run_optimization_sweep

    results = run_optimization_sweep(scenario, budget=scenario.total_intervention_budget, n_candidates=4, use_bo=False)
    assert len(results) >= 4  # at least baselines + 4 candidates
    # feasible results should come before infeasible
    for i in range(len(results) - 1):
        if not results[i].is_feasible and results[i + 1].is_feasible:
            pytest.fail("Infeasible result before feasible result in sorted output")
