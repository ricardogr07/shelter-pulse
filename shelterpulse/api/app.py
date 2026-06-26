"""FastAPI REST adapter for ShelterPulse."""
from __future__ import annotations

import dataclasses
import io
import tempfile
import zipfile
from pathlib import Path

import fastapi
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, model_validator

from shelterpulse.core.montecarlo import make_seed_set
from shelterpulse.core.schema import Scenario, load_scenario
from shelterpulse.optimize.baselines import ALL_BASELINES
from shelterpulse.optimize.interface import evaluate_candidate
from shelterpulse.optimize.workflow import CandidateAllocation, run_optimization_sweep

app = fastapi.FastAPI(title="ShelterPulse API", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

_SCENARIO_PATH = Path(__file__).parent.parent.parent / "scenarios" / "whisker_haven.yaml"
_scenario: Scenario | None = None


def _get_scenario() -> Scenario:
    global _scenario
    if _scenario is None:
        _scenario = load_scenario(_SCENARIO_PATH)
    return _scenario


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


class SweepRequest(BaseModel):
    n_candidates: int = 30
    n_replications: int = 64
    use_bo: bool = True


class EvaluationOut(BaseModel):
    foster_support: float
    clinic_hours: float
    temporary_isolation: float
    adoption_events: float
    mean_overflow_cat_days: float
    std_overflow_cat_days: float
    mean_total_cost: float
    is_feasible: bool


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "scenario": _get_scenario().name}


@app.post("/simulate", response_model=EvaluationOut)
def simulate(req: SimulateRequest) -> EvaluationOut:
    scenario = _get_scenario()
    alloc = CandidateAllocation(**req.allocation.model_dump())
    seeds = make_seed_set(scenario.seed, req.n_replications)
    er = evaluate_candidate(alloc, scenario, seeds)
    return EvaluationOut(
        **dataclasses.asdict(er.allocation),
        mean_overflow_cat_days=er.mean_overflow_cat_days,
        std_overflow_cat_days=er.std_overflow_cat_days,
        mean_total_cost=er.mean_total_cost,
        is_feasible=er.is_feasible,
    )


@app.post("/optimize", response_model=list[EvaluationOut])
def optimize(req: SweepRequest) -> list[EvaluationOut]:
    scenario = _get_scenario()
    seeds = make_seed_set(scenario.seed, req.n_replications)
    results = run_optimization_sweep(
        scenario,
        budget=scenario.total_intervention_budget,
        n_candidates=req.n_candidates,
        seed_set=seeds,
        use_bo=req.use_bo,
    )
    return [
        EvaluationOut(
            **dataclasses.asdict(r.allocation),
            mean_overflow_cat_days=r.mean_overflow_cat_days,
            std_overflow_cat_days=r.std_overflow_cat_days,
            mean_total_cost=r.mean_total_cost,
            is_feasible=r.is_feasible,
        )
        for r in results
    ]


@app.get("/baselines", response_model=dict[str, AllocationIn])
def baselines() -> dict:
    return {
        name: AllocationIn(**dataclasses.asdict(alloc))
        for name, alloc in ALL_BASELINES.items()
    }


@app.post("/export")
def export(req: SweepRequest) -> StreamingResponse:
    from shelterpulse.core.export import export_results

    scenario = _get_scenario()
    seeds = make_seed_set(scenario.seed, req.n_replications)
    results = run_optimization_sweep(
        scenario,
        budget=scenario.total_intervention_budget,
        n_candidates=req.n_candidates,
        seed_set=seeds,
        use_bo=req.use_bo,
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
