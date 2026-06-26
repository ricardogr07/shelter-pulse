from pathlib import Path

import csv as csv_mod

import pytest
import yaml

from shelterpulse.core.export import export_results
from shelterpulse.core.montecarlo import make_seed_set
from shelterpulse.core.schema import load_scenario
from shelterpulse.optimize.baselines import ALL_BASELINES
from shelterpulse.optimize.interface import evaluate_candidate

WHISKER_HAVEN = Path(__file__).parent.parent.parent / "scenarios" / "whisker_haven.yaml"


@pytest.fixture(scope="module")
def run_data():
    scenario = load_scenario(WHISKER_HAVEN)
    seeds = make_seed_set(42, 4)
    results = [evaluate_candidate(a, scenario, seeds) for a in ALL_BASELINES.values()]
    return scenario, results, seeds


def test_yaml_has_required_keys(run_data, tmp_path):
    scenario, results, seeds = run_data
    paths = export_results(scenario, results, seeds, tmp_path)
    doc = yaml.safe_load((tmp_path / "results.yaml").read_text())
    assert "scenario" in doc
    assert "seed_set" in doc
    assert "results" in doc
    assert doc["results"][0]["rank"] == 1


def test_csv_row_count(run_data, tmp_path):
    scenario, results, seeds = run_data
    export_results(scenario, results, seeds, tmp_path)
    with (tmp_path / "results.csv").open() as f:
        rows = list(csv_mod.DictReader(f))
    assert len(rows) == len(results)


def test_export_idempotent(run_data, tmp_path):
    scenario, results, seeds = run_data
    export_results(scenario, results, seeds, tmp_path)
    export_results(scenario, results, seeds, tmp_path)  # second write, no error
