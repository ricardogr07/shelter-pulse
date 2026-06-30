"""Tests for the timeline API helper (_run_timeline)."""

from pathlib import Path

from shelterpulse.api.app import _run_timeline
from shelterpulse.core.schema import load_scenario
from shelterpulse.optimize.workflow import CandidateAllocation

_SCENARIO = load_scenario(Path(__file__).parent.parent.parent / "scenarios" / "whisker_haven.yaml")


def test_timeline_returns_correct_number_of_days():
    """Timeline should return one snapshot per simulation day."""
    alloc = CandidateAllocation(0.25, 0.25, 0.25, 0.25)
    points = _run_timeline(_SCENARIO, alloc)
    assert len(points) == _SCENARIO.duration_days


def test_timeline_has_no_negative_values():
    """Housing used and overflow must never be negative."""
    alloc = CandidateAllocation(0.25, 0.25, 0.25, 0.25)
    points = _run_timeline(_SCENARIO, alloc)
    for p in points:
        assert p.housing_used >= 0
        assert p.overflow >= 0


def test_timeline_days_are_sequential():
    """Days should be numbered 1 through duration_days."""
    alloc = CandidateAllocation(0.25, 0.25, 0.25, 0.25)
    points = _run_timeline(_SCENARIO, alloc)
    days = [p.day for p in points]
    assert days == list(range(1, _SCENARIO.duration_days + 1))


def test_timeline_zero_alloc_has_more_overflow():
    """Zero allocation (no intervention) should have >= overflow than domain heuristic."""
    zero = CandidateAllocation(0, 0, 0, 0)
    heuristic = CandidateAllocation(0.40, 0.0, 0.20, 0.40)
    zero_points = _run_timeline(_SCENARIO, zero)
    heuristic_points = _run_timeline(_SCENARIO, heuristic)
    zero_overflow = sum(p.overflow for p in zero_points)
    heuristic_overflow = sum(p.overflow for p in heuristic_points)
    assert zero_overflow >= heuristic_overflow
