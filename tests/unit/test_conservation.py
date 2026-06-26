"""Conservation invariant: every cat that enters must exit via a terminal state."""

from pathlib import Path

import pytest

from shelterpulse.core.engine import run_simulation
from shelterpulse.core.schema import load_scenario

WHISKER_HAVEN = Path(__file__).parent.parent.parent / "scenarios" / "whisker_haven.yaml"


@pytest.fixture(scope="module")
def scenario():
    return load_scenario(WHISKER_HAVEN)


def test_no_cats_created_or_destroyed(scenario):
    result = run_simulation(scenario, seed=42)
    intake = result.total_intake
    terminal = result.adopted + result.transferred + result.still_in_shelter
    assert intake == terminal, (
        f"Conservation violated: {intake} intake, "
        f"{result.adopted} adopted + {result.transferred} transferred + "
        f"{result.still_in_shelter} still_in_shelter = {terminal}"
    )


def test_no_negative_counts(scenario):
    result = run_simulation(scenario, seed=42)
    assert result.total_intake >= 0
    assert result.adopted >= 0
    assert result.transferred >= 0
    assert result.still_in_shelter >= 0
    assert result.overflow_cat_days >= 0


def test_conservation_across_seeds(scenario):
    """Conservation must hold for multiple seeds, not just 42."""
    for seed in [0, 1, 99, 12345]:
        result = run_simulation(scenario, seed=seed)
        intake = result.total_intake
        terminal = result.adopted + result.transferred + result.still_in_shelter
        assert intake == terminal, f"Conservation violated for seed={seed}"


def test_positive_intake(scenario):
    """A 90-day simulation must produce at least some cats."""
    result = run_simulation(scenario, seed=42)
    assert result.total_intake > 0, "Expected non-zero intake over 90 days"
