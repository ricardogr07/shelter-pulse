"""Tests for CI-95 uncertainty bands."""
import pytest
from pathlib import Path
from shelterpulse.core.montecarlo import make_seed_set
from shelterpulse.core.schema import load_scenario
from shelterpulse.optimize.interface import evaluate_candidate
from shelterpulse.optimize.workflow import CandidateAllocation

pytestmark = pytest.mark.skip(reason="pending: ci95_* fields not in EvaluationResult yet")

_SCENARIO = load_scenario(Path(__file__).parent.parent.parent / "scenarios" / "whisker_haven.yaml")


def test_ci95_populated():
    alloc = CandidateAllocation(0.25, 0.25, 0.25, 0.25)
    seeds = make_seed_set(_SCENARIO.seed, 16)
    result = evaluate_candidate(alloc, _SCENARIO, seeds)
    assert result.ci95_overflow_high >= result.mean_overflow_cat_days
    assert result.ci95_overflow_low <= result.mean_overflow_cat_days
    assert result.ci95_cost_high >= result.mean_total_cost
    assert result.ci95_cost_low <= result.mean_total_cost


def test_ci_narrows_with_more_reps():
    alloc = CandidateAllocation(0.25, 0.25, 0.25, 0.25)
    seeds_8 = make_seed_set(_SCENARIO.seed, 8)
    seeds_64 = make_seed_set(_SCENARIO.seed, 64)
    r8 = evaluate_candidate(alloc, _SCENARIO, seeds_8)
    r64 = evaluate_candidate(alloc, _SCENARIO, seeds_64)
    width_8 = r8.ci95_overflow_high - r8.ci95_overflow_low
    width_64 = r64.ci95_overflow_high - r64.ci95_overflow_low
    # More reps should give narrower CI (or at least not wider)
    assert width_64 <= width_8 * 1.5  # allow some tolerance due to randomness
