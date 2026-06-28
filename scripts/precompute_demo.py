"""Pre-compute demo optimization results for instant serving.

Run: uv run python scripts/precompute_demo.py
Output: scenarios/whisker_haven_cache.pkl
"""
import pickle
from pathlib import Path

from shelterpulse.core.montecarlo import make_seed_set
from shelterpulse.core.schema import load_scenario
from shelterpulse.optimize.workflow import run_optimization_sweep

SCENARIO_PATH = Path(__file__).parent.parent / "scenarios" / "whisker_haven.yaml"
CACHE_PATH = Path(__file__).parent.parent / "scenarios" / "whisker_haven_cache.pkl"

N_CANDIDATES = 10
N_REPLICATIONS = 16

if __name__ == "__main__":
    print(f"Loading {SCENARIO_PATH.name}...")
    scenario = load_scenario(SCENARIO_PATH)
    seeds = make_seed_set(scenario.seed, N_REPLICATIONS)

    print(f"Running optimization sweep ({N_CANDIDATES} candidates, {N_REPLICATIONS} reps, BO=True)...")
    results = run_optimization_sweep(
        scenario,
        budget=scenario.total_intervention_budget,
        n_candidates=N_CANDIDATES,
        seed_set=seeds,
        use_bo=True,
    )

    print(f"Caching {len(results)} results to {CACHE_PATH.name}...")
    with open(CACHE_PATH, "wb") as f:
        pickle.dump(results, f)

    print("Done. Cache ready for instant demo serving.")
