"""Schema guardrails: load_scenario must validate and reject invalid input."""

from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from shelterpulse.core.schema import Scenario, load_scenario

WHISKER_HAVEN = Path(__file__).parent.parent.parent / "scenarios" / "whisker_haven.yaml"


def test_valid_scenario_loads():
    scenario = load_scenario(WHISKER_HAVEN)
    assert scenario.name == "Whisker Haven"
    assert scenario.duration_days == 90
    assert scenario.seed == 42


def test_intake_profiles_sum_to_one():
    scenario = load_scenario(WHISKER_HAVEN)
    total = sum(p.weight for p in scenario.intake_profiles)
    assert abs(total - 1.0) < 0.01, f"Profile weights sum to {total:.3f}"


def test_missing_required_field_raises():
    with pytest.raises(ValidationError):
        Scenario.model_validate({"name": "Test"})  # missing most required fields


def test_extra_field_raises():
    raw = yaml.safe_load(WHISKER_HAVEN.read_text(encoding="utf-8"))
    raw["not_a_real_field"] = "oops"
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        Scenario.model_validate(raw)


def test_negative_duration_raises():
    raw = yaml.safe_load(WHISKER_HAVEN.read_text(encoding="utf-8"))
    raw["duration_days"] = -1
    with pytest.raises(ValidationError):
        Scenario.model_validate(raw)


def test_zero_duration_raises():
    raw = yaml.safe_load(WHISKER_HAVEN.read_text(encoding="utf-8"))
    raw["duration_days"] = 0
    with pytest.raises(ValidationError):
        Scenario.model_validate(raw)


def test_profiles_not_summing_to_one_raises():
    raw = yaml.safe_load(WHISKER_HAVEN.read_text(encoding="utf-8"))
    # Set all weights to 0.5 so they don't sum to 1.0
    for profile in raw["intake_profiles"]:
        profile["weight"] = 0.5
    with pytest.raises(ValidationError, match="weights must sum to 1.0"):
        Scenario.model_validate(raw)


def test_scenario_is_frozen():
    from pydantic import ValidationError
    scenario = load_scenario(WHISKER_HAVEN)
    with pytest.raises((ValidationError, TypeError)):
        scenario.duration_days = 999  # type: ignore[misc]
