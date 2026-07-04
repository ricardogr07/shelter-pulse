"""Kernel/acquisition sensitivity ablation for the whitepaper.

Runs the Whisker Haven case study under several jaxbo GP configurations and
reports every variant's result, not just the best one. This is a
transparent sensitivity check, not a search for a configuration that beats
the baselines: the shipped optimizer (shelterpulse/optimize/jaxbo_optimizer.py)
is untouched by this script and stays exactly as validated.

Run: uv run --extra optimize python scripts/whitepaper/optimizer_sensitivity_ablation.py
"""

from __future__ import annotations

import dataclasses
import json
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
from shelterpulse.optimize.jaxbo_optimizer import _dirichlet_candidates, _from_cube, _to_cube
from shelterpulse.optimize.workflow import EvaluationResult

REPOSITORY_ROOT = Path(__file__).resolve().parent.parent.parent
SCENARIO_PATH = REPOSITORY_ROOT / "scenarios" / "whisker_haven.yaml"
OUTPUT_PATH = REPOSITORY_ROOT / "docs" / "whitepaper" / "data" / "optimizer-sensitivity.json"

N_CANDIDATES = 20
N_REPLICATIONS = 32

# Every variant tested is reported below, whatever the outcome. "current" is
# the shipped configuration (Matern52 kernel, Expected Improvement).
CONFIGS: list[dict[str, Any]] = [
    {"name": "current (Matern52 + EI)", "kernel": "Matern52", "acquisition": "EI"},
    {"name": "RBF kernel + EI", "kernel": "RBF", "acquisition": "EI"},
    {"name": "Matern52 + LCB", "kernel": "Matern52", "acquisition": "LCB"},
]


def _acquisition_values(name: str, mu, sigma, best_y_norm: float) -> np.ndarray:
    if name == "EI":
        return np.array([float(acquisitions.EI(m, s, best_y_norm)[0]) for m, s in zip(mu, sigma)])
    if name == "LCB":
        return np.array([float(acquisitions.LCB(m, s)[0]) for m, s in zip(mu, sigma)])
    raise ValueError(f"unknown acquisition {name}")


def run_variant(kernel: str, acquisition: str, scenario, seed_set, warm_start: list[EvaluationResult]) -> list[EvaluationResult]:
    """A parameterized copy of jaxbo_optimizer._jaxbo_gp_ei for ablation only.

    Deliberately duplicated rather than importing a modified production
    function: the shipped optimizer must stay exactly as validated.
    """
    rng = np.random.default_rng(scenario.seed + 7)
    n_init = max(5, min(8, N_CANDIDATES // 3))

    observations: list[EvaluationResult] = list(warm_start)
    results: list[EvaluationResult] = []
    X_obs: list[np.ndarray] = [
        _to_cube(np.array([r.allocation.foster_support, r.allocation.clinic_hours,
                            r.allocation.temporary_isolation, r.allocation.adoption_events]))
        for r in warm_start
    ]

    n_random = min(N_CANDIDATES, max(0, n_init - len(X_obs)))
    for x in _dirichlet_candidates(rng, n_random):
        er = dataclasses.replace(evaluate_candidate(_from_cube(x), scenario, seed_set), source="bo")
        results.append(er)
        observations.append(er)
        X_obs.append(x)

    n_bo = N_CANDIDATES - len(results)
    lb, ub = np.zeros(4), np.ones(4)
    prior = input_priors.uniform_prior(lb=lb, ub=ub)
    gp_options = {"kernel": kernel, "input_prior": prior}

    for _ in range(n_bo):
        X = np.array(X_obs)
        y_raw = np.array([r.mean_overflow_cat_days for r in observations])
        y_mean, y_std = y_raw.mean(), y_raw.std() + 1e-8
        y_norm = ((y_raw - y_mean) / y_std).reshape(-1, 1)
        X_norm = np.clip(X, 0.0, 1.0)
        batch = {"X": X_norm, "y": y_norm}
        bounds = {"lb": lb, "ub": ub}

        gp = GP(gp_options)
        rng_key = jax.random.PRNGKey(int(rng.integers(1 << 31)))
        params = gp.train(batch, rng_key, num_restarts=3)
        best_y_norm = float(y_norm.min())

        candidates = _dirichlet_candidates(rng, 256)
        mus, sigmas = [], []
        for cand in candidates:
            c = jnp.array(cand).reshape(1, 4)
            mu, sigma = gp.predict(c, params=params, batch=batch, bounds=bounds)
            mus.append(mu)
            sigmas.append(sigma)
        acq_vals = _acquisition_values(acquisition, mus, sigmas, best_y_norm)

        best_idx = int(np.argmin(acq_vals))
        x_next = candidates[best_idx]
        er = dataclasses.replace(evaluate_candidate(_from_cube(x_next), scenario, seed_set), source="bo")
        results.append(er)
        observations.append(er)
        X_obs.append(x_next)

    results.sort(key=lambda r: (not r.is_feasible, r.mean_overflow_cat_days))
    return results


def main() -> None:
    scenario = load_scenario(SCENARIO_PATH)
    seed_set = make_seed_set(scenario.seed, N_REPLICATIONS)

    baseline_results = [
        dataclasses.replace(evaluate_candidate(alloc, scenario, seed_set), source=f"baseline:{name}")
        for name, alloc in ALL_BASELINES.items()
    ]
    best_baseline = min(baseline_results, key=lambda r: r.mean_overflow_cat_days)

    variants = []
    for config in CONFIGS:
        started = time.perf_counter()
        results = run_variant(config["kernel"], config["acquisition"], scenario, seed_set, baseline_results)
        elapsed = time.perf_counter() - started
        best_bo = min(results, key=lambda r: r.mean_overflow_cat_days)
        variants.append({
            "config": config["name"],
            "kernel": config["kernel"],
            "acquisition": config["acquisition"],
            "best_overflow_cat_days": best_bo.mean_overflow_cat_days,
            "best_allocation": dataclasses.asdict(best_bo.allocation),
            "beats_best_baseline": best_bo.mean_overflow_cat_days < best_baseline.mean_overflow_cat_days,
            "elapsed_seconds": elapsed,
        })
        print(f"{config['name']:24s} best_overflow={best_bo.mean_overflow_cat_days:8.1f} "
              f"(best baseline={best_baseline.mean_overflow_cat_days:.1f}) "
              f"beats_baseline={variants[-1]['beats_best_baseline']} ({elapsed:.1f}s)")

    output = {
        "scenario": scenario.name,
        "best_baseline_source": best_baseline.source,
        "best_baseline_overflow_cat_days": best_baseline.mean_overflow_cat_days,
        "n_candidates": N_CANDIDATES,
        "n_replications": N_REPLICATIONS,
        "variants": variants,
        "note": (
            "All tested variants reported regardless of outcome. The shipped "
            "optimizer (shelterpulse/optimize/jaxbo_optimizer.py) is unmodified "
            "by this ablation; it always uses the 'current' configuration."
        ),
    }
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(f"\nWrote {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
