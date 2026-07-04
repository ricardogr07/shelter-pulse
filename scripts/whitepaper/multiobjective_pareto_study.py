"""True multi-objective optimizer targeting the spend/overflow Pareto
frontier directly, closing out Future Work item 3 (previously: post-hoc
analysis only, see scripts/whitepaper/pareto_budget_analysis.py).

Duplicates the GP+EI core loop from shelterpulse/optimize/jaxbo_optimizer.py
(same convention as scripts/whitepaper/optimizer_sensitivity_ablation.py) rather than
modifying the shipped optimizer, which stays exactly as validated. Two
changes from the shipped single-objective search:

1. Candidates are sampled from a 5-component Dirichlet distribution with the
   5th ("unspent budget") component dropped, instead of the shipped
   4-component Dirichlet (which always sums to 1, i.e. always spends the
   full budget). This lets candidates genuinely range from near-zero spend
   to full spend within the same validated 4D simplex machinery -
   _from_cube() already passes shares through unchanged whenever they sum
   to <= 1, so no change to CandidateAllocation, Scenario, or
   resolve_intervention() is needed.
2. The objective fed to the GP is a ParEGO-style augmented Chebyshev
   scalarization of (normalized overflow, normalized spend) at a sweep of
   preference weights, instead of raw overflow alone - this is what makes
   the search target the whole spend/overflow Pareto frontier rather than
   overflow at a single fixed budget.

Run: uv run --extra optimize python scripts/whitepaper/multiobjective_pareto_study.py
"""

from __future__ import annotations

import dataclasses
import json
import sys
import time
from pathlib import Path
from typing import Any

import jax
import jax.numpy as jnp
import numpy as np
from jaxbo import acquisitions, input_priors
from jaxbo.models import GP

from shelterpulse.core.montecarlo import make_seed_set
from shelterpulse.core.schema import load_scenario
from shelterpulse.optimize.baselines import ALL_BASELINES
from shelterpulse.optimize.interface import evaluate_candidate
from shelterpulse.optimize.jaxbo_optimizer import _from_cube
from shelterpulse.optimize.workflow import EvaluationResult

REPOSITORY_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPOSITORY_ROOT))
from scripts.whitepaper.pareto_budget_analysis import is_pareto_optimal  # noqa: E402

SCENARIO_PATH = REPOSITORY_ROOT / "scenarios" / "whisker_haven.yaml"
EXISTING_PARETO_PATH = REPOSITORY_ROOT / "docs" / "whitepaper" / "data" / "pareto-budget-analysis.json"
OUTPUT_PATH = REPOSITORY_ROOT / "docs" / "whitepaper" / "data" / "multiobjective-pareto-study.json"

N_CANDIDATES = 12
N_REPLICATIONS = 8
RHO = 0.05
WEIGHTS = [round(i / 6, 4) for i in range(7)]  # 0.0 (spend-only) ... 1.0 (overflow-only)


def _dirichlet_candidates_with_slack(rng: np.random.Generator, n: int) -> np.ndarray:
    """Sample allocations that may leave budget unspent.

    Draws from a 5-component Dirichlet and drops the 5th ("unspent") share,
    so the remaining 4 components sum to <= 1 rather than always to 1.
    """
    return rng.dirichlet([1.0, 1.0, 1.0, 1.0, 1.0], size=n)[:, :4]


def _spend(result: EvaluationResult, budget: float) -> float:
    a = result.allocation
    return (a.foster_support + a.clinic_hours + a.temporary_isolation + a.adoption_events) * budget


def _scalarize(overflow: np.ndarray, spend: np.ndarray, weight: float) -> np.ndarray:
    """ParEGO-style augmented Chebyshev scalarization of two min-max
    normalized objectives, recomputed against all observations seen so far.
    """

    def norm(x: np.ndarray) -> np.ndarray:
        lo, hi = x.min(), x.max()
        return (x - lo) / (hi - lo + 1e-8)

    overflow_n = norm(overflow)
    spend_n = norm(spend)
    weighted = weight * overflow_n + (1.0 - weight) * spend_n
    chebyshev = np.maximum(weight * overflow_n, (1.0 - weight) * spend_n)
    return weighted + RHO * chebyshev


def run_weighted_search(
    weight: float,
    scenario,
    seed_set,
    warm_start: list[EvaluationResult],
) -> list[EvaluationResult]:
    """A parameterized copy of jaxbo_optimizer._jaxbo_gp_ei for multi-objective
    search only. Deliberately duplicated, not imported, so the shipped
    single-objective optimizer stays exactly as validated.
    """
    rng = np.random.default_rng(scenario.seed + 11)
    n_init = max(5, min(8, N_CANDIDATES // 3))

    observations: list[EvaluationResult] = list(warm_start)
    results: list[EvaluationResult] = []
    X_obs: list[np.ndarray] = [
        np.array([r.allocation.foster_support, r.allocation.clinic_hours,
                   r.allocation.temporary_isolation, r.allocation.adoption_events])
        for r in warm_start
    ]

    n_random = min(N_CANDIDATES, max(0, n_init - len(X_obs)))
    for x in _dirichlet_candidates_with_slack(rng, n_random):
        er = dataclasses.replace(evaluate_candidate(_from_cube(x), scenario, seed_set), source="bo-mo")
        results.append(er)
        observations.append(er)
        X_obs.append(x)

    n_bo = N_CANDIDATES - len(results)
    lb, ub = np.zeros(4), np.ones(4)
    prior = input_priors.uniform_prior(lb=lb, ub=ub)
    gp_options = {"kernel": "Matern52", "input_prior": prior}

    for _ in range(n_bo):
        X = np.array(X_obs)
        overflow_raw = np.array([r.mean_overflow_cat_days for r in observations])
        spend_raw = np.array([_spend(r, scenario.total_intervention_budget) for r in observations])
        y_raw = _scalarize(overflow_raw, spend_raw, weight)
        y_mean, y_std = y_raw.mean(), y_raw.std() + 1e-8
        y_norm = ((y_raw - y_mean) / y_std).reshape(-1, 1)
        X_norm = np.clip(X, 0.0, 1.0)
        batch = {"X": X_norm, "y": y_norm}
        bounds = {"lb": lb, "ub": ub}

        gp = GP(gp_options)
        rng_key = jax.random.PRNGKey(int(rng.integers(1 << 31)))
        params = gp.train(batch, rng_key, num_restarts=3)
        best_y_norm = float(y_norm.min())

        candidates = _dirichlet_candidates_with_slack(rng, 256)
        ei_vals = []
        for cand in candidates:
            c = jnp.array(cand).reshape(1, 4)
            mu, sigma = gp.predict(c, params=params, batch=batch, bounds=bounds)
            ei_vals.append(float(acquisitions.EI(mu, sigma, best_y_norm)[0]))

        best_idx = int(np.argmin(ei_vals))  # EI returns negative
        x_next = candidates[best_idx]
        er = dataclasses.replace(evaluate_candidate(_from_cube(x_next), scenario, seed_set), source="bo-mo")
        results.append(er)
        observations.append(er)
        X_obs.append(x_next)

    results.sort(key=lambda r: (not r.is_feasible, r.mean_overflow_cat_days))
    return results


def main() -> None:
    scenario = load_scenario(SCENARIO_PATH)
    seed_set = make_seed_set(scenario.seed, N_REPLICATIONS)
    budget = scenario.total_intervention_budget

    baseline_results = [
        dataclasses.replace(evaluate_candidate(alloc, scenario, seed_set), source=f"baseline:{name}")
        for name, alloc in ALL_BASELINES.items()
    ]

    pooled: list[dict[str, Any]] = []
    for r in baseline_results:
        pooled.append({"source": r.source, "spend": _spend(r, budget), "overflow": r.mean_overflow_cat_days})

    per_weight_summary = []
    for weight in WEIGHTS:
        started = time.perf_counter()
        results = run_weighted_search(weight, scenario, seed_set, baseline_results)
        elapsed = time.perf_counter() - started
        mo_results = [r for r in results if r.source == "bo-mo"]
        for r in mo_results:
            pooled.append({
                "source": f"bo-mo w={weight:.3f}",
                "spend": _spend(r, budget),
                "overflow": r.mean_overflow_cat_days,
            })

        overflow_raw = np.array([r.mean_overflow_cat_days for r in mo_results])
        spend_raw = np.array([_spend(r, budget) for r in mo_results])
        scalarized = _scalarize(overflow_raw, spend_raw, weight)
        best = mo_results[int(np.argmin(scalarized))]
        per_weight_summary.append({
            "weight": weight,
            "best_spend": _spend(best, budget),
            "best_overflow": best.mean_overflow_cat_days,
            "best_allocation": dataclasses.asdict(best.allocation),
            "elapsed_seconds": elapsed,
        })
        print(f"weight={weight:.3f}  best_spend=${_spend(best, budget):7.0f}  "
              f"best_overflow={best.mean_overflow_cat_days:8.1f}  ({elapsed:.1f}s)")

    # Merge in the existing (separate) fractional-budget sweep + deduplicated
    # Whisker Haven evidence, so the final frontier reflects both studies.
    if EXISTING_PARETO_PATH.exists():
        existing = json.loads(EXISTING_PARETO_PATH.read_text(encoding="utf-8"))
        seen = {(round(p["spend"], 1), round(p["overflow"], 1)) for p in pooled}
        for p in existing["points"]:
            key = (round(p["spend"], 1), round(p["overflow"], 1))
            if key in seen:
                continue
            seen.add(key)
            pooled.append({"source": p["source"], "spend": p["spend"], "overflow": p["overflow"]})

    for point in pooled:
        point["pareto_optimal"] = is_pareto_optimal(point, pooled)

    frontier = [p for p in pooled if p["pareto_optimal"]]
    frontier.sort(key=lambda p: p["spend"])

    output = {
        "scenario": scenario.name,
        "total_intervention_budget": budget,
        "n_candidates_per_weight": N_CANDIDATES,
        "n_replications": N_REPLICATIONS,
        "weights": WEIGHTS,
        "per_weight_summary": per_weight_summary,
        "pooled_points": pooled,
        "pareto_frontier": frontier,
        "note": (
            "Candidates sampled with a 5-component Dirichlet (4 spending "
            "shares + 1 dropped 'unspent' share) so spend genuinely varies "
            "within the search, scalarized via ParEGO-style augmented "
            "Chebyshev across 7 preference weights targeting the "
            "spend/overflow frontier directly. The shipped optimizer "
            "(shelterpulse/optimize/jaxbo_optimizer.py) is unmodified by "
            "this script. Pooled with the separate fractional-budget sweep "
            "in pareto-budget-analysis.json for the final joint frontier."
        ),
    }
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(f"\nJoint Pareto frontier ({len(frontier)} points):")
    for p in frontier:
        print(f"  {p['source']:35s} spend=${p['spend']:7.0f} overflow={p['overflow']:8.1f}")
    print(f"\nWrote {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
