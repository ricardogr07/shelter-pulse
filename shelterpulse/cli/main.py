"""Typer CLI for ShelterPulse — thin adapter over core, no simulation logic here."""
from __future__ import annotations
import json
from pathlib import Path
import typer

app = typer.Typer(help="ShelterPulse — shelter simulation & optimization CLI")
_DEFAULT_SCENARIO = Path(__file__).parent.parent.parent / "scenarios" / "whisker_haven.yaml"


@app.command()
def simulate(
    foster: float = typer.Option(0.25, help="Foster support budget share (0-1)"),
    clinic: float = typer.Option(0.25, help="Clinic hours budget share (0-1)"),
    isolation: float = typer.Option(0.25, help="Temporary isolation budget share (0-1)"),
    adoption: float = typer.Option(0.25, help="Adoption events budget share (0-1)"),
    reps: int = typer.Option(64, help="Monte Carlo replications"),
    scenario: Path = typer.Option(_DEFAULT_SCENARIO, "--scenario", help="Path to scenario YAML"),
    output_json: bool = typer.Option(False, "--json", help="Output as JSON"),
    quiet: bool = typer.Option(False, "--quiet", help="Suppress progress output"),
) -> None:
    """Run the shelter simulation with a given budget allocation."""
    from shelterpulse.core.schema import load_scenario
    from shelterpulse.optimize.workflow import CandidateAllocation
    from shelterpulse.optimize.interface import evaluate_candidate
    from shelterpulse.core.montecarlo import make_seed_set

    if not quiet and not output_json:
        typer.echo("Loading scenario...")
    sc = load_scenario(scenario)
    alloc = CandidateAllocation(foster_support=foster, clinic_hours=clinic,
                                 temporary_isolation=isolation, adoption_events=adoption)
    seeds = make_seed_set(sc.seed, reps)
    if not quiet and not output_json:
        typer.echo("Running simulation...")
    result = evaluate_candidate(alloc, sc, seeds)

    if output_json:
        typer.echo(json.dumps({
            "scenario": sc.name,
            "allocation": {
                "foster_support": foster, "clinic_hours": clinic,
                "temporary_isolation": isolation, "adoption_events": adoption,
            },
            "mean_overflow_cat_days": result.mean_overflow_cat_days,
            "std_overflow_cat_days": result.std_overflow_cat_days,
            "mean_total_cost": result.mean_total_cost,
            "is_feasible": result.is_feasible,
            "ci95_overflow_low": result.ci95_overflow_low,
            "ci95_overflow_high": result.ci95_overflow_high,
        }))
    else:
        typer.echo(f"Scenario:        {sc.name}")
        typer.echo(f"Replications:    {reps}")
        typer.echo(f"Mean overflow:   {result.mean_overflow_cat_days:.1f} cat-days")
        typer.echo(f"Std overflow:    {result.std_overflow_cat_days:.1f}")
        typer.echo(f"Mean cost:       ${result.mean_total_cost:,.2f}")
        typer.echo(f"Feasible:        {result.is_feasible}")


@app.command()
def optimize(
    candidates: int = typer.Option(30, help="Number of candidates"),
    reps: int = typer.Option(64, help="Replications per candidate"),
    bo: bool = typer.Option(True, "--bo/--no-bo", help="Use Bayesian Optimization"),
    top: int = typer.Option(5, help="Top results to display"),
    scenario: Path = typer.Option(_DEFAULT_SCENARIO, "--scenario", help="Path to scenario YAML"),
    output_json: bool = typer.Option(False, "--json", help="Output as JSON"),
    quiet: bool = typer.Option(False, "--quiet", help="Suppress progress output"),
) -> None:
    """Run the full optimization sweep and print top-ranked allocations."""
    from shelterpulse.core.schema import load_scenario
    from shelterpulse.optimize.workflow import run_optimization_sweep
    from shelterpulse.core.montecarlo import make_seed_set

    if not quiet and not output_json:
        typer.echo("Loading scenario...")
    sc = load_scenario(scenario)
    seeds = make_seed_set(sc.seed, reps)
    if not quiet and not output_json:
        typer.echo(f"Running sweep ({candidates} candidates, {reps} reps each)...")
    results = run_optimization_sweep(sc, budget=sc.total_intervention_budget,
                                     n_candidates=candidates, seed_set=seeds, use_bo=bo)
    if output_json:
        typer.echo(json.dumps({
            "scenario": sc.name,
            "results": [
                {
                    "rank": i + 1,
                    "foster_support": r.allocation.foster_support,
                    "clinic_hours": r.allocation.clinic_hours,
                    "temporary_isolation": r.allocation.temporary_isolation,
                    "adoption_events": r.allocation.adoption_events,
                    "mean_overflow_cat_days": r.mean_overflow_cat_days,
                    "mean_total_cost": r.mean_total_cost,
                    "is_feasible": r.is_feasible,
                }
                for i, r in enumerate(results[:top])
            ],
        }))
    else:
        typer.echo(f"\nTop {top} results:")
        typer.echo(f"{'Rank':<5} {'Foster':>7} {'Clinic':>7} {'Iso':>7} {'Adopt':>7} {'Overflow':>10} {'Cost':>12}")
        typer.echo("-" * 65)
        for i, r in enumerate(results[:top]):
            a = r.allocation
            typer.echo(f"{i+1:<5} {a.foster_support:>7.2f} {a.clinic_hours:>7.2f} "
                       f"{a.temporary_isolation:>7.2f} {a.adoption_events:>7.2f} "
                       f"{r.mean_overflow_cat_days:>10.1f} ${r.mean_total_cost:>10,.0f}")


@app.command()
def baselines() -> None:
    """Print the named baseline allocations."""
    from shelterpulse.optimize.baselines import ALL_BASELINES
    typer.echo(f"{'Name':<20} {'Foster':>7} {'Clinic':>7} {'Iso':>7} {'Adopt':>7}")
    typer.echo("-" * 50)
    for name, alloc in ALL_BASELINES.items():
        typer.echo(f"{name:<20} {alloc.foster_support:>7.2f} {alloc.clinic_hours:>7.2f} "
                   f"{alloc.temporary_isolation:>7.2f} {alloc.adoption_events:>7.2f}")


@app.command()
def export(
    out_dir: Path = typer.Argument(Path("./results"), help="Output directory"),
    candidates: int = typer.Option(30),
    reps: int = typer.Option(64),
    bo: bool = typer.Option(True, "--bo/--no-bo"),
    scenario: Path = typer.Option(_DEFAULT_SCENARIO, "--scenario", help="Path to scenario YAML"),
) -> None:
    """Run sweep and export results to YAML + CSV."""
    from shelterpulse.core.schema import load_scenario
    from shelterpulse.optimize.workflow import run_optimization_sweep
    from shelterpulse.core.montecarlo import make_seed_set
    from shelterpulse.core.export import export_results

    sc = load_scenario(scenario)
    seeds = make_seed_set(sc.seed, reps)
    results = run_optimization_sweep(sc, budget=sc.total_intervention_budget,
                                     n_candidates=candidates, seed_set=seeds, use_bo=bo)
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = export_results(sc, results, seeds, out_dir)
    typer.echo(f"Exported: {', '.join(str(p) for p in paths)}")
