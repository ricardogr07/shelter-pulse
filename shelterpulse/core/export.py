"""Reproducible export: scenario assumptions, seed set, and results to YAML + CSV."""
from __future__ import annotations

import csv
import dataclasses
from pathlib import Path

import yaml

from shelterpulse.core.schema import Scenario
from shelterpulse.optimize.workflow import EvaluationResult


def export_results(
    scenario: Scenario,
    results: list[EvaluationResult],
    seed_set: list[int],
    out_dir: Path,
) -> list[Path]:
    """Write YAML + CSV to out_dir. Returns list of written file paths."""
    yaml_path = out_dir / "results.yaml"
    csv_path = out_dir / "results.csv"

    _write_yaml(scenario, results, seed_set, yaml_path)
    _write_csv(results, csv_path)

    return [yaml_path, csv_path]


def _write_yaml(
    scenario: Scenario,
    results: list[EvaluationResult],
    seed_set: list[int],
    path: Path,
) -> None:
    doc = {
        "scenario": {
            "name": scenario.name,
            "version": scenario.version,
            "duration_days": scenario.duration_days,
            "seed": scenario.seed,
            "n_replications": scenario.n_replications,
            "total_intervention_budget": scenario.total_intervention_budget,
        },
        "seed_set": seed_set,
        "n_candidates_evaluated": len(results),
        "results": [
            {
                "rank": i + 1,
                "foster_support": r.allocation.foster_support,
                "clinic_hours": r.allocation.clinic_hours,
                "temporary_isolation": r.allocation.temporary_isolation,
                "adoption_events": r.allocation.adoption_events,
                "mean_overflow_cat_days": round(r.mean_overflow_cat_days, 2),
                "std_overflow_cat_days": round(r.std_overflow_cat_days, 2),
                "mean_total_cost": round(r.mean_total_cost, 2),
                "is_feasible": r.is_feasible,
            }
            for i, r in enumerate(results)
        ],
    }
    path.write_text(yaml.dump(doc, sort_keys=False, allow_unicode=True), encoding="utf-8")


def _write_csv(results: list[EvaluationResult], path: Path) -> None:
    fields = [
        "rank", "foster_support", "clinic_hours", "temporary_isolation",
        "adoption_events", "mean_overflow_cat_days", "std_overflow_cat_days",
        "mean_total_cost", "is_feasible",
    ]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for i, r in enumerate(results):
            writer.writerow({
                "rank": i + 1,
                "foster_support": r.allocation.foster_support,
                "clinic_hours": r.allocation.clinic_hours,
                "temporary_isolation": r.allocation.temporary_isolation,
                "adoption_events": r.allocation.adoption_events,
                "mean_overflow_cat_days": round(r.mean_overflow_cat_days, 2),
                "std_overflow_cat_days": round(r.std_overflow_cat_days, 2),
                "mean_total_cost": round(r.mean_total_cost, 2),
                "is_feasible": r.is_feasible,
            })
