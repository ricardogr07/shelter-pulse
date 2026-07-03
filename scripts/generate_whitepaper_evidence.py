"""Generate machine-readable evidence for the ShelterPulse whitepaper.

This command intentionally runs the public optimization seam rather than using
hand-authored result tables. The output captures the exact configuration,
environment, ranking, and uncertainty values used by the paper.
"""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import importlib.metadata
import json
import platform
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path

from shelterpulse.core.montecarlo import make_seed_set
from shelterpulse.core.schema import load_scenario
from shelterpulse.optimize.baselines import ALL_BASELINES
from shelterpulse.optimize.workflow import run_optimization_sweep


REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SCENARIO = REPOSITORY_ROOT / "scenarios" / "whisker_haven.yaml"
DEFAULT_OUTPUT = (
    REPOSITORY_ROOT
    / "docs"
    / "whitepaper"
    / "evidence"
    / "whisker-haven.json"
)
EVIDENCE_INPUTS = (
    "scenarios/whisker_haven.yaml",
    "shelterpulse/core/engine.py",
    "shelterpulse/core/interventions.py",
    "shelterpulse/optimize/interface.py",
    "shelterpulse/optimize/jaxbo_optimizer.py",
    "shelterpulse/optimize/workflow.py",
)


def _git_revision() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=REPOSITORY_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _source_digests() -> dict[str, str]:
    return {
        relative_path: hashlib.sha256(
            (REPOSITORY_ROOT / relative_path).read_bytes()
        ).hexdigest()
        for relative_path in EVIDENCE_INPUTS
    }


def _package_versions() -> dict[str, str | None]:
    versions: dict[str, str | None] = {}
    for package in ("numpy", "simpy", "jax", "jaxbo"):
        try:
            versions[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            versions[package] = None
    return versions


def generate_evidence(
    scenario_path: Path,
    candidates: int,
    replications: int,
) -> dict:
    scenario = load_scenario(scenario_path)
    seeds = make_seed_set(scenario.seed, replications)

    started = time.perf_counter()
    results = run_optimization_sweep(
        scenario,
        budget=scenario.total_intervention_budget,
        n_candidates=candidates,
        seed_set=seeds,
        use_bo=True,
    )
    elapsed_seconds = time.perf_counter() - started

    serialized_results = []
    for rank, result in enumerate(results, start=1):
        row = dataclasses.asdict(result)
        row["rank"] = rank
        row["source"] = result.source
        row["allocated_intervention_spend"] = (
            sum(dataclasses.asdict(result.allocation).values())
            * scenario.total_intervention_budget
        )
        serialized_results.append(row)

    return {
        "schema_version": 1,
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "git_commit": _git_revision(),
        "source_sha256": _source_digests(),
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "packages": _package_versions(),
        },
        "configuration": {
            "scenario": scenario.name,
            "scenario_path": str(scenario_path.relative_to(REPOSITORY_ROOT)),
            "scenario_seed": scenario.seed,
            "seed_set": seeds,
            "bo_candidates": candidates,
            "baselines": list(ALL_BASELINES),
            "replications_per_allocation": replications,
            "total_intervention_budget": scenario.total_intervention_budget,
        },
        "elapsed_seconds": elapsed_seconds,
        "results": serialized_results,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", type=Path, default=DEFAULT_SCENARIO)
    parser.add_argument("--candidates", type=int, default=20)
    parser.add_argument("--replications", type=int, default=32)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    evidence = generate_evidence(
        args.scenario.resolve(),
        args.candidates,
        args.replications,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "output": str(args.output),
        "git_commit": evidence["git_commit"],
        "elapsed_seconds": evidence["elapsed_seconds"],
        "winner": evidence["results"][0],
    }, indent=2))


if __name__ == "__main__":
    main()
