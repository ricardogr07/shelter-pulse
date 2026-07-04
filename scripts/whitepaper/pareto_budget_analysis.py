"""Budget-vs-overflow tradeoff for the whitepaper's multi-objective discussion.

"Minimize overflow at minimum budget" is a different question from "which
candidate wins at a fixed $5,000 budget": every candidate evaluated so far
(BO and named baselines alike) spends either $0 (zero intervention) or the
full budget, since Dirichlet-sampled allocation shares always sum to 1. This
script evaluates the winning shape (all-in-events) at fractional budget
levels using the existing evaluate_candidate() interface - no new simulation
mechanics, no optimizer or production code change - and reports every point,
then marks which points are Pareto-optimal (no other evaluated point has
both lower spend and lower overflow).
"""

from __future__ import annotations

import json
from pathlib import Path

from shelterpulse.core.montecarlo import make_seed_set
from shelterpulse.core.schema import load_scenario
from shelterpulse.optimize.interface import evaluate_candidate
from shelterpulse.optimize.workflow import CandidateAllocation

REPOSITORY_ROOT = Path(__file__).resolve().parent.parent.parent
SCENARIO_PATH = REPOSITORY_ROOT / "scenarios" / "whisker_haven.yaml"
EVIDENCE_PATH = REPOSITORY_ROOT / "docs" / "whitepaper" / "evidence" / "whisker-haven.json"
OUTPUT_PATH = REPOSITORY_ROOT / "docs" / "whitepaper" / "data" / "pareto-budget-analysis.json"

N_REPLICATIONS = 32
BUDGET_FRACTIONS = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]


def is_pareto_optimal(point: dict, all_points: list[dict]) -> bool:
    """No other point has both lower or equal spend and lower or equal
    overflow, with at least one strictly lower (standard Pareto dominance).
    """
    for other in all_points:
        if other is point:
            continue
        not_worse = (
            other["spend"] <= point["spend"] and other["overflow"] <= point["overflow"]
        )
        strictly_better = (
            other["spend"] < point["spend"] or other["overflow"] < point["overflow"]
        )
        if not_worse and strictly_better:
            return False
    return True


def main() -> None:
    scenario = load_scenario(SCENARIO_PATH)
    seeds = make_seed_set(scenario.seed, N_REPLICATIONS)

    points: list[dict] = []

    # Fractional-budget sweep of the winning allocation shape.
    for fraction in BUDGET_FRACTIONS:
        alloc = CandidateAllocation(0.0, 0.0, 0.0, fraction)
        result = evaluate_candidate(alloc, scenario, seeds)
        points.append({
            "source": f"all_in_events @ {fraction:.0%} budget",
            "spend": fraction * scenario.total_intervention_budget,
            "overflow": result.mean_overflow_cat_days,
        })
        print(f"all_in_events @ {fraction:.0%}: spend=${fraction * scenario.total_intervention_budget:.0f} "
              f"overflow={result.mean_overflow_cat_days:.1f}")

    # Existing evidence: every already-evaluated baseline and BO candidate,
    # deduplicated by (spend, overflow) so the frontier isn't cluttered.
    evidence = json.loads(EVIDENCE_PATH.read_text(encoding="utf-8"))
    seen = set()
    for row in evidence["results"]:
        spend = sum(row["allocation"].values()) * scenario.total_intervention_budget
        overflow = row["mean_overflow_cat_days"]
        key = (round(spend, 1), round(overflow, 1))
        if key in seen:
            continue
        seen.add(key)
        points.append({"source": row["source"], "spend": spend, "overflow": overflow})

    for point in points:
        point["pareto_optimal"] = is_pareto_optimal(point, points)

    frontier = [p for p in points if p["pareto_optimal"]]
    frontier.sort(key=lambda p: p["spend"])

    output = {
        "scenario": scenario.name,
        "total_intervention_budget": scenario.total_intervention_budget,
        "n_replications": N_REPLICATIONS,
        "points": points,
        "pareto_frontier": frontier,
        "note": (
            "Fractional-budget points evaluate the all_in_events allocation "
            "shape at less than full spend using the existing evaluate_candidate() "
            "interface. Full-budget points are deduplicated from the Whisker "
            "Haven evidence file (BO candidates and named baselines)."
        ),
    }
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(f"\nPareto frontier ({len(frontier)} points):")
    for p in frontier:
        print(f"  {p['source']:35s} spend=${p['spend']:7.0f} overflow={p['overflow']:8.1f}")
    print(f"\nWrote {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
