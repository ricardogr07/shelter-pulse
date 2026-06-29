"""Tests for timeline recording in the simulation engine."""
import pytest
from pathlib import Path
from shelterpulse.core.schema import load_scenario

pytestmark = pytest.mark.skip(reason="pending: DailySnapshot and record_timeline not in engine yet")

_SCENARIO = load_scenario(Path(__file__).parent.parent.parent / "scenarios" / "whisker_haven.yaml")


def test_timeline_returns_snapshots():
    result = run_simulation(_SCENARIO, seed=42, record_timeline=True)
    assert result.timeline is not None
    assert len(result.timeline) == _SCENARIO.duration_days
    assert all(isinstance(s, DailySnapshot) for s in result.timeline)


def test_timeline_disabled_by_default():
    result = run_simulation(_SCENARIO, seed=42)
    assert result.timeline is None


def test_timeline_has_intake():
    result = run_simulation(_SCENARIO, seed=42, record_timeline=True)
    total_intake_from_timeline = sum(s.intake_today for s in result.timeline)
    assert total_intake_from_timeline == result.total_intake
