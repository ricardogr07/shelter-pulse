"""Tests for sensitivity analysis (unit-level, no HTTP)."""
import pytest
from pathlib import Path
from shelterpulse.core.montecarlo import make_seed_set
from shelterpulse.core.schema import load_scenario
from shelterpulse.optimize.interface import evaluate_candidate
from shelterpulse.optimize.workflow import CandidateAllocation

_SCENARIO = load_scenario(Path(__file__).parent.parent.parent / "scenarios" / "whisker_haven.yaml")


def test_different_intake_rates_give_different_overflow():
    """Higher intake should produce more overflow."""
    from shelterpulse.core.schema import Scenario
    import yaml
    raw = yaml.safe_load(Path(Path(__file__).parent.parent.parent / "scenarios" / "whisker_haven.yaml").read_text())
    seeds = make_seed_set(42, 8)
    zero = CandidateAllocation(0.0, 0.0, 0.0, 0.0)

    # Base
    base_s = Scenario.model_validate(raw)
    base_r = evaluate_candidate(zero, base_s, seeds)

    # High intake
    raw_high = dict(raw)
    raw_high["intake_rate_per_day"] = raw["intake_rate_per_day"] * 1.5
    high_s = Scenario.model_validate(raw_high)
    high_r = evaluate_candidate(zero, high_s, seeds)

    assert high_r.mean_overflow_cat_days > base_r.mean_overflow_cat_days
