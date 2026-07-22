"""FastAPI REST adapter for ShelterPulse."""
from __future__ import annotations

import dataclasses
import io
import json
import logging
import tempfile
import time
import zipfile
from pathlib import Path
from uuid import uuid4

import fastapi
import numpy as np
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, model_validator

logger = logging.getLogger(__name__)

from shelterpulse.core.montecarlo import make_seed_set
from shelterpulse.core.schema import Scenario, load_scenario
from shelterpulse.optimize.baselines import ALL_BASELINES
from shelterpulse.optimize.interface import evaluate_candidate
from shelterpulse.optimize.workflow import CandidateAllocation, run_optimization_sweep
from shelterpulse.store import get_runs_for_shelter, init_schema, log_consent, save_run
from shelterpulse.api.rate_limit import (
    check_rate_limit,
    export_limiter,
    get_client_ip,
    optimize_limiter,
    simulate_limiter,
)

_ALLOWED_ORIGINS = [
    "https://shelter-pulse.com",
    "http://localhost:3000",
    "http://localhost:8000",
]

app = fastapi.FastAPI(title="ShelterPulse API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOWED_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


@app.middleware("http")
async def _log_requests(request: fastapi.Request, call_next):
    """Single point of request/response logging for every route.

    Cheaper than annotating each handler individually - covers current and
    future endpoints alike. Never logs headers/body (may contain
    X-Internal-Key or scenario data).
    """
    start = time.monotonic()
    response = await call_next(request)
    elapsed_ms = (time.monotonic() - start) * 1000
    logger.info(
        "%s %s -> %d (%.1fms)",
        request.method, request.url.path, response.status_code, elapsed_ms,
    )
    return response


@app.on_event("startup")
def _startup() -> None:
    """Initialize DuckDB schema on app startup."""
    try:
        init_schema()
    except Exception:
        # Non-fatal: store is optional (duckdb may not be installed in all envs)
        pass

_SCENARIO_PATH = Path(__file__).parent.parent.parent / "scenarios" / "whisker_haven.yaml"
_CACHE_PATH = Path(__file__).parent.parent.parent / "scenarios" / "whisker_haven_cache.json"
_scenario: Scenario | None = None


def _get_scenario() -> Scenario:
    global _scenario
    if _scenario is None:
        _scenario = load_scenario(_SCENARIO_PATH)
    return _scenario


def _load_demo_cache() -> list | None:
    if _CACHE_PATH.exists():
        with open(_CACHE_PATH, "r", encoding="utf-8") as f:
            rows = json.load(f)
        from shelterpulse.optimize.workflow import CandidateAllocation, EvaluationResult
        return [
            EvaluationResult(
                allocation=CandidateAllocation(**row["allocation"]),
                mean_overflow_cat_days=row["mean_overflow_cat_days"],
                std_overflow_cat_days=row["std_overflow_cat_days"],
                mean_total_cost=row["mean_total_cost"],
                is_feasible=row["is_feasible"],
                ci95_overflow_low=row.get("ci95_overflow_low", 0.0),
                ci95_overflow_high=row.get("ci95_overflow_high", 0.0),
                ci95_cost_low=row.get("ci95_cost_low", 0.0),
                ci95_cost_high=row.get("ci95_cost_high", 0.0),
                source=row.get("source", "candidate"),
            )
            for row in rows
        ]
    return None


# ── Request / Response models ─────────────────────────────────────────────────

class AllocationIn(BaseModel):
    foster_support: float = 0.25
    clinic_hours: float = 0.25
    temporary_isolation: float = 0.25
    adoption_events: float = 0.25

    @model_validator(mode="after")
    def shares_bounded(self) -> "AllocationIn":
        total = self.foster_support + self.clinic_hours + self.temporary_isolation + self.adoption_events
        if total > 1.0 + 1e-6:
            raise ValueError(f"shares sum to {total:.3f}, must be <= 1.0")
        return self


class SimulateRequest(BaseModel):
    allocation: AllocationIn = AllocationIn()
    n_replications: int = 64

    @model_validator(mode="after")
    def clamp_replications(self) -> "SimulateRequest":
        if self.n_replications < 1:
            raise ValueError("n_replications must be >= 1")
        if self.n_replications > 128:
            raise ValueError("n_replications must be <= 128")
        return self


class SweepRequest(BaseModel):
    n_candidates: int = 30
    n_replications: int = 64
    use_bo: bool = True

    @model_validator(mode="after")
    def clamp_params(self) -> "SweepRequest":
        if self.n_candidates < 1 or self.n_candidates > 50:
            raise ValueError("n_candidates must be between 1 and 50")
        if self.n_replications < 1 or self.n_replications > 128:
            raise ValueError("n_replications must be between 1 and 128")
        return self


class EvaluationOut(BaseModel):
    foster_support: float
    clinic_hours: float
    temporary_isolation: float
    adoption_events: float
    mean_overflow_cat_days: float
    std_overflow_cat_days: float
    mean_total_cost: float
    is_feasible: bool
    ci95_overflow_low: float = 0.0
    ci95_overflow_high: float = 0.0
    ci95_cost_low: float = 0.0
    ci95_cost_high: float = 0.0
    source: str = "candidate"


class BuilderRequest(BaseModel):
    """Simplified 9-field form from the UI custom builder."""
    duration_days: int = 90
    housing_capacity: int = 35
    isolation_slots: int = 5
    vet_tech_fte: float = 1.5
    intervention_budget: float = 5000.0
    mean_intake_per_day: float = 3.8
    kitten_fraction: float = 0.59
    base_adoption_rate: float = 0.08
    n_replications: int = 32
    allocation: AllocationIn | None = None
    # Consent and metadata
    consent_storage: bool = False
    is_test_data: bool = False
    name: str = "My Shelter"

    @model_validator(mode="after")
    def clamp_params(self) -> "BuilderRequest":
        if self.duration_days < 1 or self.duration_days > 365:
            raise ValueError("duration_days must be between 1 and 365")
        if self.housing_capacity < 1 or self.housing_capacity > 500:
            raise ValueError("housing_capacity must be between 1 and 500")
        if self.isolation_slots < 0 or self.isolation_slots > 100:
            raise ValueError("isolation_slots must be between 0 and 100")
        if self.vet_tech_fte < 0.1 or self.vet_tech_fte > 20.0:
            raise ValueError("vet_tech_fte must be between 0.1 and 20.0")
        if self.intervention_budget < 0 or self.intervention_budget > 1_000_000:
            raise ValueError("intervention_budget must be between 0 and 1,000,000")
        if self.mean_intake_per_day < 0.1 or self.mean_intake_per_day > 50.0:
            raise ValueError("mean_intake_per_day must be between 0.1 and 50.0")
        if self.kitten_fraction < 0.0 or self.kitten_fraction > 1.0:
            raise ValueError("kitten_fraction must be between 0.0 and 1.0")
        if self.base_adoption_rate < 0.0 or self.base_adoption_rate > 1.0:
            raise ValueError("base_adoption_rate must be between 0.0 and 1.0")
        if self.n_replications < 1 or self.n_replications > 128:
            raise ValueError("n_replications must be between 1 and 128")
        return self


class SensitivityPoint(BaseModel):
    param: str
    direction: str   # "high" or "low"
    delta: float     # ±20%
    mean_overflow_cat_days: float


class TimelinePoint(BaseModel):
    day: int
    housing_used: int
    overflow: int


# ── Helpers ───────────────────────────────────────────────────────────────────

def _er_to_out(r) -> EvaluationOut:
    return EvaluationOut(
        **dataclasses.asdict(r.allocation),
        mean_overflow_cat_days=r.mean_overflow_cat_days,
        std_overflow_cat_days=r.std_overflow_cat_days,
        mean_total_cost=r.mean_total_cost,
        is_feasible=r.is_feasible,
        ci95_overflow_low=r.ci95_overflow_low,
        ci95_overflow_high=r.ci95_overflow_high,
        ci95_cost_low=r.ci95_cost_low,
        ci95_cost_high=r.ci95_cost_high,
        source=r.source,
    )


def _builder_to_scenario(req: BuilderRequest) -> Scenario:
    """Build a minimal Scenario from builder form fields."""
    import yaml
    base_raw = yaml.safe_load(_SCENARIO_PATH.read_text(encoding="utf-8"))

    # Patch the relevant fields
    base_raw["duration_days"] = req.duration_days
    base_raw["housing_capacity"] = req.housing_capacity
    base_raw["isolation_capacity"] = req.isolation_slots
    base_raw["total_intervention_budget"] = req.intervention_budget
    base_raw["intake_rate_per_day"] = req.mean_intake_per_day

    # Adjust foster network to a sane fraction of housing
    base_raw["foster_network"]["capacity"] = max(1, req.housing_capacity // 4)

    # Scale workforce vet_tech fte
    for w in base_raw["workforce"]:
        if w["role"] == "vet_tech":
            w["fte"] = req.vet_tech_fte

    # Rebuild intake profiles from kitten_fraction
    kf = max(0.01, min(0.99, req.kitten_fraction))
    af = 1.0 - kf
    base_raw["intake_profiles"] = [
        {"age_class": "weaned_kitten", "health_status": "healthy", "weight": round(kf * 0.6, 4)},
        {"age_class": "neonatal", "health_status": "medical_hold", "weight": round(kf * 0.4, 4)},
        {"age_class": "adult", "health_status": "healthy", "weight": round(af * 0.7, 4)},
        {"age_class": "adult", "health_status": "isolation_required", "weight": round(af * 0.3, 4)},
    ]
    # Normalise weights to sum exactly to 1.0
    weights: list[float] = [float(p["weight"]) for p in base_raw["intake_profiles"]]
    total = sum(weights)
    for p in base_raw["intake_profiles"]:
        p["weight"] = round(float(p["weight"]) / total, 6)

    return Scenario.model_validate(base_raw)


# ── Core endpoints ────────────────────────────────────────────────────────────

@app.get("/health")
def health() -> dict:
    return {"status": "ok", "scenario": _get_scenario().name}


@app.post("/simulate", response_model=EvaluationOut)
def simulate(req: SimulateRequest, request: fastapi.Request) -> EvaluationOut:
    check_rate_limit(simulate_limiter, request)
    scenario = _get_scenario()
    alloc = CandidateAllocation(**req.allocation.model_dump())
    seeds = make_seed_set(scenario.seed, req.n_replications)
    return _er_to_out(evaluate_candidate(alloc, scenario, seeds))


@app.post("/optimize", response_model=list[EvaluationOut])
def optimize(req: SweepRequest, request: fastapi.Request) -> list[EvaluationOut]:
    check_rate_limit(optimize_limiter, request)
    # Cache hit for demo params (must match scripts/precompute_demo.py: 10 candidates, 16 reps, BO)
    if req.n_candidates == 10 and req.n_replications == 16 and req.use_bo:
        cached = _load_demo_cache()
        if cached:
            return [_er_to_out(r) for r in cached]

    scenario = _get_scenario()
    seeds = make_seed_set(scenario.seed, req.n_replications)
    results = run_optimization_sweep(
        scenario, budget=scenario.total_intervention_budget,
        n_candidates=req.n_candidates, seed_set=seeds, use_bo=req.use_bo,
    )
    return [_er_to_out(r) for r in results]


@app.get("/baselines", response_model=dict[str, AllocationIn])
def baselines() -> dict:
    return {name: AllocationIn(**dataclasses.asdict(alloc)) for name, alloc in ALL_BASELINES.items()}


# ── Builder endpoints ─────────────────────────────────────────────────────────

@app.post("/simulate/builder", response_model=EvaluationOut)
def simulate_builder(req: BuilderRequest, request: fastapi.Request) -> EvaluationOut:
    check_rate_limit(simulate_limiter, request)
    scenario = _builder_to_scenario(req)
    alloc = CandidateAllocation(**(req.allocation.model_dump() if req.allocation else {"foster_support": 0.25, "clinic_hours": 0.25, "temporary_isolation": 0.25, "adoption_events": 0.25}))
    seeds = make_seed_set(scenario.seed, req.n_replications)
    return _er_to_out(evaluate_candidate(alloc, scenario, seeds))


@app.post("/optimize/builder", response_model=list[EvaluationOut])
def optimize_builder(req: BuilderRequest, request: fastapi.Request) -> list[EvaluationOut]:
    """Run BO optimization on a custom builder scenario, synchronously."""
    check_rate_limit(optimize_limiter, request)
    scenario = _builder_to_scenario(req)
    seeds = make_seed_set(scenario.seed, req.n_replications)
    results = run_optimization_sweep(
        scenario, budget=req.intervention_budget,
        n_candidates=15, seed_set=seeds, use_bo=True,
    )
    # Persist if user consented
    if req.consent_storage:
        try:
            import dataclasses as dc
            sync_job_id = str(uuid4())
            result_dicts = [
                {**dc.asdict(r.allocation), "mean_overflow_cat_days": r.mean_overflow_cat_days,
                 "std_overflow_cat_days": r.std_overflow_cat_days, "mean_total_cost": r.mean_total_cost,
                 "is_feasible": r.is_feasible, "ci95_overflow_low": r.ci95_overflow_low,
                 "ci95_overflow_high": r.ci95_overflow_high, "ci95_cost_low": r.ci95_cost_low,
                 "ci95_cost_high": r.ci95_cost_high}
                for r in results
            ]
            save_run(sync_job_id, req.model_dump(), result_dicts, consent=True, is_test=req.is_test_data)
        except Exception:
            pass  # Non-fatal: store may not be initialized
    # Always log the consent decision (even when declined) for audit trail
    try:
        log_consent(str(uuid4()), get_client_ip(request), req.consent_storage, req.is_test_data)
    except Exception:
        pass  # Non-fatal: store may not be initialized
    return [_er_to_out(r) for r in results]


# ── Run history ───────────────────────────────────────────────────────────────


@app.get("/runs/recent")
def get_recent_runs_endpoint(
    name: str | None = fastapi.Query(None, description="Shelter name to match"),
    housing_capacity: int | None = fastapi.Query(None, description="Housing capacity"),
    isolation_slots: int | None = fastapi.Query(None, description="Isolation slots"),
    intervention_budget: float | None = fastapi.Query(None, description="Budget"),
    limit: int = fastapi.Query(10, ge=1, le=50),
):
    """Fetch recent optimization runs.

    If name + params are provided, filters to matching shelter.
    If no params, returns all recent consented runs (global history).
    """
    try:
        if name and housing_capacity is not None and isolation_slots is not None and intervention_budget is not None:
            runs = get_runs_for_shelter(
                name=name,
                housing_capacity=housing_capacity,
                isolation_slots=isolation_slots,
                intervention_budget=intervention_budget,
                limit=limit,
            )
        else:
            from shelterpulse.store import get_recent_runs
            runs = get_recent_runs(limit=limit)
    except Exception:
        runs = []
    # Convert datetime objects to ISO strings for JSON serialization
    for run in runs:
        if run.get("created_at"):
            run["created_at"] = run["created_at"].isoformat()
    return runs


@app.get("/runs/analytics")
def get_run_analytics():
    """Aggregate statistics across all consented, non-test runs."""
    try:
        from shelterpulse.store import get_analytics
        return get_analytics()
    except Exception:
        return {}


class CompareOut(BaseModel):
    winner: EvaluationOut
    baselines: dict[str, EvaluationOut]


@app.post("/optimize/builder/compare", response_model=CompareOut)
def optimize_builder_compare(req: BuilderRequest, request: fastapi.Request) -> CompareOut:
    """Run BO optimization + evaluate all baselines against a custom scenario."""
    check_rate_limit(optimize_limiter, request)
    scenario = _builder_to_scenario(req)
    seeds = make_seed_set(scenario.seed, req.n_replications)
    results = run_optimization_sweep(
        scenario, budget=req.intervention_budget,
        n_candidates=15, seed_set=seeds, use_bo=True,
    )
    winner = results[0]
    baseline_results = {
        name: _er_to_out(evaluate_candidate(alloc, scenario, list(seeds)))
        for name, alloc in ALL_BASELINES.items()
    }
    return CompareOut(winner=_er_to_out(winner), baselines=baseline_results)


# ── Sensitivity endpoint ──────────────────────────────────────────────────────

def _sensitivity_points(alloc: CandidateAllocation, seeds: list[int], raw: dict) -> list[SensitivityPoint]:
    """Vary intake_rate, housing_capacity, isolation_capacity ±20%; return 6 SensitivityPoints."""
    import yaml
    from shelterpulse.core.schema import Scenario as Sc
    params = {
        "intake_rate_per_day": raw["intake_rate_per_day"],
        "housing_capacity": raw["housing_capacity"],
        "isolation_capacity": raw["isolation_capacity"],
    }
    points: list[SensitivityPoint] = []
    for param, base_val in params.items():
        for direction, delta in [("high", 1.2), ("low", 0.8)]:
            patched = dict(raw)
            patched[param] = max(1, int(base_val * delta)) if isinstance(base_val, int) else base_val * delta
            overflow = evaluate_candidate(alloc, Sc.model_validate(patched), seeds).mean_overflow_cat_days
            points.append(SensitivityPoint(param=param, direction=direction, delta=delta, mean_overflow_cat_days=overflow))
    return points


@app.post("/sensitivity", response_model=list[SensitivityPoint])
def sensitivity(req: SimulateRequest) -> list[SensitivityPoint]:
    """Tornado chart data for Whisker Haven demo scenario."""
    import yaml
    alloc = CandidateAllocation(**req.allocation.model_dump())
    seeds = make_seed_set(_get_scenario().seed, req.n_replications)
    raw = yaml.safe_load(_SCENARIO_PATH.read_text(encoding="utf-8"))
    return _sensitivity_points(alloc, seeds, raw)


@app.post("/sensitivity/builder", response_model=list[SensitivityPoint])
def sensitivity_builder(req: BuilderRequest) -> list[SensitivityPoint]:
    """Tornado chart data for a custom builder scenario."""
    import yaml
    scenario = _builder_to_scenario(req)
    alloc = CandidateAllocation(0.25, 0.25, 0.25, 0.25)
    seeds = make_seed_set(scenario.seed, req.n_replications)
    # Build raw dict from builder params for patching
    raw = yaml.safe_load(_SCENARIO_PATH.read_text(encoding="utf-8"))
    raw["intake_rate_per_day"] = req.mean_intake_per_day
    raw["housing_capacity"] = req.housing_capacity
    raw["isolation_capacity"] = req.isolation_slots
    return _sensitivity_points(alloc, seeds, raw)


# ── Timeline endpoints ────────────────────────────────────────────────────────

def _run_timeline(scenario, alloc: CandidateAllocation) -> list[TimelinePoint]:
    """Daily housing occupancy + overflow for one simulation run (seed=scenario.seed).

    overflow = cats queued for housing (above capacity). simpy.Resource.count is
    capped at capacity, so the housing queue length is the real "above capacity" signal.
    """
    import simpy

    from shelterpulse.core.engine import (
        _Counters,
        _build_resources,
        _generate_arrivals,
        _intake_generator,
    )
    from shelterpulse.core.interventions import resolve_intervention

    intervention = resolve_intervention(
        alloc.foster_support, alloc.clinic_hours,
        alloc.temporary_isolation, alloc.adoption_events, scenario,
    )

    env = simpy.Environment()
    resources = _build_resources(env, scenario, intervention)
    counters = _Counters()
    arrivals = _generate_arrivals(scenario, scenario.seed)
    daily_snapshots: list[dict] = []

    def _daily_sampler():
        for day in range(scenario.duration_days):
            yield env.timeout(24.0)
            daily_snapshots.append({
                "day": day + 1,
                "housing_used": resources["housing"].count,
                "overflow": len(resources["housing"].queue),
            })

    env.process(_intake_generator(
        env, scenario, resources, counters, arrivals, scenario.seed,
        intervention.adoption_wait_multiplier,
        intervention.vet_service_time_multiplier,
        intervention.foster_coordination_time_multiplier,
    ))
    env.process(_daily_sampler())
    # +1h past the last 24h boundary: SimPy does not run events scheduled exactly at
    # `until`, so without this the final daily sample (at day*24) is dropped — a 1-day
    # scenario would return an empty timeline and an N-day one only N-1 points.
    env.run(until=scenario.duration_days * 24.0 + 1.0)

    return [TimelinePoint(**s) for s in daily_snapshots]


@app.post("/simulate/timeline", response_model=list[TimelinePoint])
def simulate_timeline(req: SimulateRequest) -> list[TimelinePoint]:
    """Daily housing_used + overflow for the Whisker Haven demo scenario."""
    alloc = CandidateAllocation(**req.allocation.model_dump())
    return _run_timeline(_get_scenario(), alloc)


@app.post("/simulate/timeline/builder", response_model=list[TimelinePoint])
def simulate_timeline_builder(req: BuilderRequest) -> list[TimelinePoint]:
    """Daily housing_used + overflow for a custom builder scenario."""
    alloc = CandidateAllocation(**req.allocation.model_dump()) if req.allocation else CandidateAllocation(0.25, 0.25, 0.25, 0.25)
    return _run_timeline(_builder_to_scenario(req), alloc)


class TimelineCompareOut(BaseModel):
    before: list[TimelinePoint]
    after: list[TimelinePoint]


@app.post("/simulate/timeline/builder/compare", response_model=TimelineCompareOut)
def simulate_timeline_builder_compare(req: BuilderRequest) -> TimelineCompareOut:
    """Before/after timeline: zero allocation vs provided allocation."""
    scenario = _builder_to_scenario(req)
    alloc = CandidateAllocation(**req.allocation.model_dump()) if req.allocation else CandidateAllocation(0.25, 0.25, 0.25, 0.25)
    before = _run_timeline(scenario, CandidateAllocation(0, 0, 0, 0))
    after = _run_timeline(scenario, alloc)
    return TimelineCompareOut(before=before, after=after)


# ── Export endpoint ───────────────────────────────────────────────────────────

@app.post("/export")
def export(req: SweepRequest, request: fastapi.Request) -> StreamingResponse:
    check_rate_limit(export_limiter, request)
    from shelterpulse.core.export import export_results

    scenario = _get_scenario()
    seeds = make_seed_set(scenario.seed, req.n_replications)
    results = run_optimization_sweep(
        scenario, budget=scenario.total_intervention_budget,
        n_candidates=req.n_candidates, seed_set=seeds, use_bo=req.use_bo,
    )
    with tempfile.TemporaryDirectory() as tmp:
        out_dir = Path(tmp)
        paths = export_results(scenario, results, seeds, out_dir)
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for p in paths:
                zf.write(p, p.name)
        buf.seek(0)
        return StreamingResponse(
            buf,
            media_type="application/zip",
            headers={"Content-Disposition": "attachment; filename=shelterpulse-results.zip"},
        )
