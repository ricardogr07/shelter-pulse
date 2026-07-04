"""Generate data-driven figures for the whitepaper from evidence JSON.

Every figure here is produced directly from a committed evidence artifact,
no hand-drawn or hand-edited charts. Run after regenerating evidence:

    uv run python scripts/whitepaper/generate_whitepaper_figures.py
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

matplotlib.use("Agg")

REPOSITORY_ROOT = Path(__file__).resolve().parent.parent.parent
WHISKER_HAVEN_EVIDENCE = REPOSITORY_ROOT / "docs" / "whitepaper" / "evidence" / "whisker-haven.json"
GENERALIZATION_STUDY = REPOSITORY_ROOT / "docs" / "whitepaper" / "data" / "generalization-study.json"
PARETO_ANALYSIS = REPOSITORY_ROOT / "docs" / "whitepaper" / "data" / "pareto-budget-analysis.json"
MULTIOBJECTIVE_STUDY = REPOSITORY_ROOT / "docs" / "whitepaper" / "data" / "multiobjective-pareto-study.json"
FIGURES_DIR = REPOSITORY_ROOT / "docs" / "whitepaper" / "figures"

# Muted, print-friendly palette (colorblind-safe-ish, no reliance on red/green alone)
COLOR_BASELINE = "#6b7280"
COLOR_BO = "#2563eb"
COLOR_BEST = "#16a34a"


def _label(source: str) -> str:
    if source.startswith("baseline:"):
        return source.removeprefix("baseline:").replace("_", " ")
    if source == "bo":
        return "BO candidate"
    return source


def figure_whisker_haven_results() -> None:
    """Bar chart: mean overflow cat-days by strategy, Whisker Haven case study."""
    data = json.loads(WHISKER_HAVEN_EVIDENCE.read_text(encoding="utf-8"))
    results = sorted(data["results"], key=lambda r: r["mean_overflow_cat_days"])
    best_bo = next(r for r in results if r["source"] == "bo")
    # Keep baselines plus the single best BO candidate, matching the paper's table.
    rows = [r for r in results if r["source"].startswith("baseline:")] + [best_bo]
    rows.sort(key=lambda r: r["mean_overflow_cat_days"])

    labels = [_label(r["source"]) for r in rows]
    values = [r["mean_overflow_cat_days"] for r in rows]
    colors = [COLOR_BEST if r is best_bo else COLOR_BASELINE for r in rows]

    fig, ax = plt.subplots(figsize=(6.5, 3.2))
    bars = ax.barh(labels, values, color=colors)
    ax.invert_yaxis()
    ax.set_xlabel("Mean overflow cat-days")
    ax.set_title("Whisker Haven: overflow by strategy")
    for bar, value in zip(bars, values):
        ax.text(bar.get_width() + max(values) * 0.01, bar.get_y() + bar.get_height() / 2,
                f"{value:.1f}", va="center", fontsize=8)
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "whisker-haven-results.png", dpi=200)
    plt.close(fig)


def figure_allocation_convergence() -> None:
    """Scatter: each BO candidate's adoption-events share vs. mean overflow,
    with named baselines overlaid, illustrating whether BO's candidates
    converge toward the winning baseline's allocation shape.
    """
    data = json.loads(WHISKER_HAVEN_EVIDENCE.read_text(encoding="utf-8"))
    bo_rows = [r for r in data["results"] if r["source"] == "bo"]
    baseline_rows = [r for r in data["results"] if r["source"].startswith("baseline:")]

    fig, ax = plt.subplots(figsize=(6.5, 3.5))
    ax.scatter(
        [r["allocation"]["adoption_events"] for r in bo_rows],
        [r["mean_overflow_cat_days"] for r in bo_rows],
        color=COLOR_BO, label="BO candidates", zorder=3, s=28,
    )
    ax.scatter(
        [r["allocation"]["adoption_events"] for r in baseline_rows],
        [r["mean_overflow_cat_days"] for r in baseline_rows],
        color=COLOR_BASELINE, marker="D", label="Named baselines", zorder=3, s=40,
    )
    for r in baseline_rows:
        ax.annotate(
            _label(r["source"]),
            (r["allocation"]["adoption_events"], r["mean_overflow_cat_days"]),
            fontsize=7, xytext=(4, 4), textcoords="offset points",
        )
    ax.set_xlabel("Adoption-events budget share")
    ax.set_ylabel("Mean overflow cat-days")
    ax.set_title("BO candidates vs. baselines: allocation shape and outcome")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "allocation-convergence.png", dpi=200)
    plt.close(fig)


def figure_generalization_summary() -> None:
    """Grouped bar chart: beat/matched/worse counts, v1 (wide ranges) vs.
    v2 (narrowed toward Whisker Haven's own congested configuration).
    """
    v1_path = GENERALIZATION_STUDY.parent / "v1" / "generalization-study.json"
    if not GENERALIZATION_STUDY.exists():
        print(f"skip: {GENERALIZATION_STUDY} not found yet")
        return

    v2 = json.loads(GENERALIZATION_STUDY.read_text(encoding="utf-8"))["summary"]
    v1 = json.loads(v1_path.read_text(encoding="utf-8"))["summary"] if v1_path.exists() else None

    labels = ["beat", "matched", "worse"]
    v2_values = [v2["beat_count"], v2["matched_count"], v2["worse_count"]]

    fig, ax = plt.subplots(figsize=(5.5, 3.2))
    x = range(len(labels))
    width = 0.35 if v1 else 0.6

    if v1:
        v1_values = [v1["beat_count"], v1["matched_count"], v1["worse_count"]]
        ax.bar([i - width / 2 for i in x], v1_values, width, label=f"v1 ({v1['scenario_count']} scenarios)", color=COLOR_BASELINE)
        ax.bar([i + width / 2 for i in x], v2_values, width, label=f"v2 ({v2['scenario_count']} scenarios)", color=COLOR_BO)
        ax.legend(fontsize=8)
    else:
        ax.bar(list(x), v2_values, width, color=COLOR_BO)

    ax.set_xticks(list(x))
    ax.set_xticklabels(labels)
    ax.set_ylabel("Scenario count")
    ax.set_title("BO vs. best baseline across generalization studies")
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "generalization-summary.png", dpi=200)
    plt.close(fig)


def figure_pareto_budget() -> None:
    """Spend vs. overflow, with the Pareto frontier highlighted."""
    if not PARETO_ANALYSIS.exists():
        print(f"skip: {PARETO_ANALYSIS} not found yet")
        return

    data = json.loads(PARETO_ANALYSIS.read_text(encoding="utf-8"))
    points = data["points"]
    frontier = sorted(data["pareto_frontier"], key=lambda p: p["spend"])

    fig, ax = plt.subplots(figsize=(6.5, 3.5))
    non_frontier = [p for p in points if not p["pareto_optimal"]]
    ax.scatter([p["spend"] for p in non_frontier], [p["overflow"] for p in non_frontier],
               color=COLOR_BASELINE, alpha=0.5, s=24, label="Dominated candidates (BO + other baselines)")
    ax.plot([p["spend"] for p in frontier], [p["overflow"] for p in frontier],
            color=COLOR_BEST, marker="o", markersize=5, linewidth=1.5,
            label="Pareto frontier (all-in-events at each spend level)")
    ax.set_xlabel("Intervention spend (USD)")
    ax.set_ylabel("Mean overflow cat-days")
    ax.set_title("Budget vs. overflow: the efficient frontier")
    ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "pareto-budget.png", dpi=200)
    plt.close(fig)


def figure_multiobjective_pareto() -> None:
    """Spend vs. overflow across the multi-objective ParEGO search (all
    preference weights pooled) plus the existing fractional-budget sweep,
    with the joint Pareto frontier highlighted.
    """
    if not MULTIOBJECTIVE_STUDY.exists():
        print(f"skip: {MULTIOBJECTIVE_STUDY} not found yet")
        return

    data = json.loads(MULTIOBJECTIVE_STUDY.read_text(encoding="utf-8"))
    points = data["pooled_points"]
    frontier = sorted(data["pareto_frontier"], key=lambda p: p["spend"])

    baselines = [p for p in points if p["source"].startswith("baseline:")]
    bo_mo = [p for p in points if p["source"].startswith("bo-mo")]
    other = [p for p in points if not p["source"].startswith("baseline:") and not p["source"].startswith("bo-mo")]

    fig, ax = plt.subplots(figsize=(6.5, 3.5))
    ax.scatter([p["spend"] for p in other], [p["overflow"] for p in other],
               color=COLOR_BASELINE, alpha=0.4, s=18, label="Fractional-budget sweep")
    ax.scatter([p["spend"] for p in bo_mo], [p["overflow"] for p in bo_mo],
               color=COLOR_BO, alpha=0.6, s=22, label="Multi-objective BO candidates")
    ax.scatter([p["spend"] for p in baselines], [p["overflow"] for p in baselines],
               color=COLOR_BASELINE, marker="D", s=40, label="Named baselines")
    ax.plot([p["spend"] for p in frontier], [p["overflow"] for p in frontier],
            color=COLOR_BEST, marker="o", markersize=5, linewidth=1.5,
            label="Joint Pareto frontier")
    ax.set_xlabel("Intervention spend (USD)")
    ax.set_ylabel("Mean overflow cat-days")
    ax.set_title("Multi-objective search: spend/overflow frontier")
    ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "multiobjective-pareto.png", dpi=200)
    plt.close(fig)


def _diagram_box(ax, x, y, w, h, text, color=COLOR_BASELINE, dashed=False):
    b = FancyBboxPatch(
        (x, y), w, h, boxstyle="round,pad=0.08", linewidth=1.4,
        edgecolor=color, facecolor="white", linestyle="dashed" if dashed else "solid",
    )
    ax.add_patch(b)
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=8)
    return (x, y, w, h)


def _diagram_arrow(ax, src, dst):
    x0, y0 = src[0] + src[2], src[1] + src[3] / 2
    x1, y1 = dst[0], dst[1] + dst[3] / 2
    ax.add_patch(FancyArrowPatch(
        (x0, y0), (x1, y1), arrowstyle="-|>", mutation_scale=12,
        color="#374151", linewidth=1.2,
    ))


def figure_cat_lifecycle_diagram() -> None:
    """Schematic of the cat lifecycle modeled in engine.py's _cat_process(),
    intake through exit. Not data-driven - a fixed process diagram, not a
    plotted result - generated programmatically so it doesn't wait on an
    external design tool.
    """
    fig, ax = plt.subplots(figsize=(8.0, 3.2))
    ax.set_xlim(0, 9.2)
    ax.set_ylim(0, 3.6)
    ax.axis("off")

    intake = _diagram_box(ax, 0.2, 1.4, 1.3, 0.8, "Intake")
    assess = _diagram_box(ax, 1.9, 1.4, 1.4, 0.8, "Assessment\n(vet tech)")
    isolation = _diagram_box(ax, 3.7, 0.2, 1.5, 0.8, "Isolation\n(if required)", dashed=True)
    clearance = _diagram_box(ax, 3.7, 1.4, 1.5, 0.8, "Clearance")
    foster = _diagram_box(ax, 5.6, 2.3, 1.4, 0.8, "Foster")
    housing = _diagram_box(ax, 5.6, 0.5, 1.6, 0.8, "Housing\n(queue = overflow)")
    exit_box = _diagram_box(ax, 7.5, 1.4, 1.6, 0.8, "Adoption or\ntransfer (exit)")

    _diagram_arrow(ax, intake, assess)
    _diagram_arrow(ax, assess, isolation)
    _diagram_arrow(ax, assess, clearance)
    _diagram_arrow(ax, isolation, clearance)
    _diagram_arrow(ax, clearance, foster)
    _diagram_arrow(ax, clearance, housing)
    _diagram_arrow(ax, foster, exit_box)
    _diagram_arrow(ax, housing, exit_box)

    ax.set_title("Cat lifecycle: intake through exit", fontsize=10)
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "cat-lifecycle.png", dpi=200)
    plt.close(fig)


def figure_intervention_effects_diagram() -> None:
    """Schematic of what each of the four intervention levers mechanistically
    changes in the simulation, singling out adoption_events as the only
    lever that changes cats' exit rate rather than capacity or processing
    speed. Not data-driven - illustrates the mechanism behind the
    Limitations discussion of why all-in-events dominates.
    """
    levers = [
        ("foster_support", "adds capacity", "extra_foster_slots", COLOR_BASELINE),
        ("extra_clinic_hours", "speeds processing", "vet_service_time_multiplier", COLOR_BASELINE),
        ("temporary_isolation", "adds capacity", "extra_isolation_slots", COLOR_BASELINE),
        ("adoption_events", "increases outflow rate", "adoption_wait_multiplier", COLOR_BEST),
    ]

    fig, ax = plt.subplots(figsize=(8.0, 2.6))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 3)
    ax.axis("off")

    w, h, gap = 2.1, 1.1, 0.35
    x = 0.2
    for name, mechanism, field, color in levers:
        ax.add_patch(FancyBboxPatch(
            (x, 1.2), w, h, boxstyle="round,pad=0.08",
            linewidth=1.6, edgecolor=color, facecolor="white",
        ))
        ax.text(x + w / 2, 1.2 + h * 0.65, name, ha="center", va="center", fontsize=8, fontweight="bold")
        ax.text(x + w / 2, 1.2 + h * 0.3, mechanism, ha="center", va="center", fontsize=7.5, color=color)
        ax.text(x + w / 2, 0.85, field, ha="center", va="center", fontsize=6.5, style="italic", color="#6b7280")
        x += w + gap

    ax.set_title("What each intervention lever mechanistically changes", fontsize=10)
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "intervention-effects.png", dpi=200)
    plt.close(fig)


def main() -> None:
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    figure_whisker_haven_results()
    figure_allocation_convergence()
    figure_generalization_summary()
    figure_pareto_budget()
    figure_multiobjective_pareto()
    figure_cat_lifecycle_diagram()
    figure_intervention_effects_diagram()
    print(f"Figures written to {FIGURES_DIR}")


if __name__ == "__main__":
    main()
