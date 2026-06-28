"""Tests for CLI --json and --scenario flags."""
import json
import pytest
from pathlib import Path
from typer.testing import CliRunner
from shelterpulse.cli.main import app

runner = CliRunner()
SCENARIO = Path(__file__).parent.parent.parent / "scenarios" / "whisker_haven.yaml"

pytestmark = pytest.mark.skip(reason="pending: CLI --json/--scenario/--quiet flags not implemented yet")

def test_simulate_json_output():
    result = runner.invoke(app, ["simulate", "--json", "--reps", "8"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert "mean_overflow_cat_days" in data
    assert "allocation" in data
    assert isinstance(data["is_feasible"], bool)

def test_simulate_custom_scenario():
    result = runner.invoke(app, ["simulate", "--scenario", str(SCENARIO), "--json", "--reps", "8"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["scenario"] == "Whisker Haven"

def test_optimize_json_output():
    result = runner.invoke(app, ["optimize", "--json", "--candidates", "4", "--reps", "8", "--no-bo"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert "results" in data
    assert len(data["results"]) >= 1
    assert "rank" in data["results"][0]

def test_quiet_suppresses_progress():
    result = runner.invoke(app, ["simulate", "--quiet", "--reps", "8"])
    assert result.exit_code == 0
    assert "Loading" not in result.output
    assert "Running" not in result.output

def test_default_behavior_unchanged():
    result = runner.invoke(app, ["simulate", "--reps", "8"])
    assert result.exit_code == 0
    assert "Mean overflow" in result.output
