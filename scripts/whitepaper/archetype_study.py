"""Named scenario archetypes: does the best-baseline-beats-BO pattern hold
when a DIFFERENT resource is the binding constraint?

Distinct from scripts/whitepaper/generalization_study.py, which samples randomized
scenarios to test statistical generalization. This runs deliberately
designed, individually interpretable scenarios (scenarios/archetype_*.yaml),
each isolating one resource as the binding constraint, plus a well-resourced
control. For each archetype: the same 5-baseline + BO evidence pipeline
already used for Whisker Haven, plus a utilization diagnostic (via
run_simulation directly) reporting which resource actually bound, so "housing
was the constraint here" is a measured claim.

Run: uv run --extra optimize python scripts/whitepaper/archetype_study.py
"""

from __future__ import annotations

import dataclasses
import json
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from shelterpulse.core.engine import run_simulation
from shelterpulse.core.interventions import resolve_intervention
from shelterpulse.core.montecarlo import make_seed_set
from shelterpulse.core.schema import load_scenario
from shelterpulse.optimize.baselines import ALL_BASELINES
from shelterpulse.optimize.workflow import run_optimization_sweep

REPOSITORY_ROOT = Path(__file__).resolve().parent.parent.parent
SCENARIOS_DIR = REPOSITORY_ROOT / "scenarios"
OUTPUT_DIR = REPOSITORY_ROOT / "docs" / "whitepaper" / "data" / "archetypes"

N_CANDIDATES = 15
N_REPLICATIONS = 16
MATCH_TOLERANCE_CAT_DAYS = 1.0

ARCHETYPES = [
    "archetype_tight_housing",
    "archetype_minimal_animal_care",
    "archetype_scarce_foster",
    "archetype_minimal_budget",
    "archetype_isolation_pressure",
    "archetype_vet_tech_shortage",
    "archetype_ample_capacity",
]


def classify(results: list, all_baselines_count: int) -> dict[str, Any]:
    baseline_results = [r for r in results if r.source.startswith("baseline:")]
    bo_results = [r for r in results if r.source == "bo"]
    if len(baseline_results) != all_baselines_count:
        raise ValueError(f"expected {all_baselines_count} baseline results, got {len(baseline_results)}")
    if not bo_results:
        raise ValueError("no BO candidates in results")

    best_baseline = min(baseline_results, key=lambda r: r.mean_overflow_cat_days)
    best_bo = min(bo_results, key=lambda r: r.mean_overflow_cat_days)
    diff = best_bo.mean_overflow_cat_days - best_baseline.mean_overflow_cat_days

    if abs(diff) <= MATCH_TOLERANCE_CAT_DAYS:
        outcome = "matched"
    elif diff < 0:
        outcome = "beat"
    else:
        outcome = "worse"

    return {
        "best_baseline_source": best_baseline.source,
        "best_baseline_overflow": best_baseline.mean_overflow_cat_days,
        "best_bo_source": "bo",
        "best_bo_overflow": best_bo.mean_overflow_cat_days,
        "best_bo_allocation": dataclasses.asdict(best_bo.allocation),
        "absolute_difference": diff,
        "outcome": outcome,
    }


def utilization_diagnostic(scenario, allocation_shares: dict[str, float], seeds: list[int]) -> dict[str, float]:
    """Average utilization/queue metrics across the seed set for one
    allocation, via run_simulation directly (not the aggregated
    EvaluationResult, which doesn't expose these fields).
    """
    intervention = resolve_intervention(
        allocation_shares["foster_support"],
        allocation_shares["clinic_hours"],
        allocation_shares["temporary_isolation"],
        allocation_shares["adoption_events"],
        scenario,
    )
    fields = [
        "vet_tech_utilization", "animal_care_utilization",
        "foster_coordinator_utilization", "peak_isolation_queue",
        "peak_housing_occupancy", "overflow_cat_days",
    ]
    totals = {f: 0.0 for f in fields}
    for seed in seeds:
        result = run_simulation(scenario, seed=seed, intervention=intervention)
        for f in fields:
            totals[f] += getattr(result, f)
    return {f: totals[f] / len(seeds) for f in fields}


def run_archetype(name: str) -> dict[str, Any]:
    scenario = load_scenario(SCENARIOS_DIR / f"{name}.yaml")
    seeds = make_seed_set(scenario.seed, N_REPLICATIONS)

    started = time.perf_counter()
    results = run_optimization_sweep(
        scenario, budget=scenario.total_intervention_budget,
        n_candidates=N_CANDIDATES, seed_set=seeds, use_bo=True,
    )
    elapsed = time.perf_counter() - started

    outcome = classify(results, len(ALL_BASELINES))

    # Utilization diagnostic under zero intervention (what actually binds
    # with no extra funding) and under the winning strategy.
    zero_util = utilization_diagnostic(
        scenario, {"foster_support": 0, "clinic_hours": 0, "temporary_isolation": 0, "adoption_events": 0}, seeds,
    )
    winner = min(results, key=lambda r: r.mean_overflow_cat_days)
    winner_util = utilization_diagnostic(scenario, dataclasses.asdict(winner.allocation), seeds)

    return {
        "archetype": name,
        "scenario_name": scenario.name,
        "housing_capacity": scenario.housing_capacity,
        "isolation_capacity": scenario.isolation_capacity,
        "foster_capacity": scenario.foster_network.capacity,
        "vet_tech_fte": next(w.fte for w in scenario.workforce if w.role.value == "vet_tech"),
        "animal_care_fte": next(w.fte for w in scenario.workforce if w.role.value == "animal_care"),
        "total_intervention_budget": scenario.total_intervention_budget,
        "n_candidates": N_CANDIDATES,
        "n_replications": N_REPLICATIONS,
        "elapsed_seconds": elapsed,
        "zero_intervention_utilization": zero_util,
        "winner_utilization": winner_util,
        **outcome,
    }


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    all_results = []
    for name in ARCHETYPES:
        print(f"Running {name}...")
        result = run_archetype(name)
        all_results.append(result)
        (OUTPUT_DIR / f"{name}.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print(f"  {result['outcome']:8s} best_bo={result['best_bo_overflow']:8.1f} "
              f"best_baseline={result['best_baseline_overflow']:8.1f} [{result['best_baseline_source']}] "
              f"({result['elapsed_seconds']:.1f}s)")
        print(f"  zero-intervention utilization: vet_tech={result['zero_intervention_utilization']['vet_tech_utilization']:.2f} "
              f"animal_care={result['zero_intervention_utilization']['animal_care_utilization']:.2f} "
              f"peak_housing={result['zero_intervention_utilization']['peak_housing_occupancy']:.0f}/{result['housing_capacity']} "
              f"peak_isolation_queue={result['zero_intervention_utilization']['peak_isolation_queue']:.0f}")

    summary_path = OUTPUT_DIR / "summary.json"
    summary_path.write_text(json.dumps({
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "n_candidates": N_CANDIDATES,
        "n_replications": N_REPLICATIONS,
        "archetypes": all_results,
    }, indent=2) + "\n", encoding="utf-8")
    print(f"\nWrote {summary_path}")


if __name__ == "__main__":
    main()
