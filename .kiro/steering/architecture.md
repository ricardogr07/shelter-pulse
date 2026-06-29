---
inclusion: always
---

# ShelterPulse: Architecture Reference

Director-level context for kiro workers. Read this before making any structural change. The invariants below are enforced by CI and must not be broken.

---

## Module map

Every file, one-line purpose:

```
shelterpulse/core/schema.py          Pydantic v2: Scenario (frozen), CatIntakeProfile, SimulationResult, all domain models
shelterpulse/core/engine.py          SimPy DES: run_simulation(), _cat_process(), _intake_generator(), _metrics_sampler()
shelterpulse/core/interventions.py   resolve_intervention(): budget shares → InterventionParams (concrete resource deltas)
shelterpulse/core/montecarlo.py      run_paired(): CRN across seed set → MonteCarloSummary (mean/std/95% CI)
shelterpulse/core/export.py          export_results(): YAML + CSV reproducible output

shelterpulse/optimize/interface.py   evaluate_candidate(): THE seam: all optimizers call this, nothing else
shelterpulse/optimize/workflow.py    run_optimization_sweep(): baselines + BO candidates → ranked list[EvaluationResult]
shelterpulse/optimize/baselines.py   5 named allocations: equal, all_in_foster, all_in_events, domain_heuristic, zero
shelterpulse/optimize/jaxbo_optimizer.py  GP+EI (jax primary, scipy fallback); simplex→cube projection

shelterpulse/api/app.py              FastAPI: /simulate, /optimize, /simulate/builder, /optimize/builder,
                                     /sensitivity, /simulate/timeline, /export, /baselines
shelterpulse/cli/main.py             Typer: simulate, optimize, baselines, export commands

ui/                                  Next.js + React + TypeScript + Tailwind; calls /api/* via fetch
scenarios/whisker_haven.yaml         Demo scenario; loaded lazily by _get_scenario() in api/app.py
```

---

## Invariants that must never be broken

**1. Core purity**
`shelterpulse/core/` imports nothing from `shelterpulse.api`, `shelterpulse.cli`, or `shelterpulse.optimize`.
Enforced by `tests/unit/test_no_cross_imports.py` in CI. Violations cause import-cycle bugs that are hard to trace.

**2. CRN discipline**
All candidates in a sweep are evaluated with the **same** `seed_set`. The seed set is created once in `workflow.run_optimization_sweep()` and passed unchanged to every `evaluate_candidate()` call.
Reason: CRN (common random numbers) ensures outcome differences are from the allocation, not Monte Carlo noise. Giving different seeds to different candidates silently invalidates the ranking.

**3. Frozen Scenario**
`Scenario` is `ConfigDict(frozen=True)`. Never add mutable fields.
Reason: a simulation sweep evaluates many candidates against the same `Scenario` object. Mutation between evaluations would corrupt results without raising an error.

**4. Single evaluation seam**
All optimizers call `evaluate_candidate(allocation, scenario, seed_set)` in `interface.py`. No optimizer calls `run_simulation()` directly.
Reason: one place to change replication logic, CRN behavior, and cost accumulation. Also maps 1:1 to a Temporal activity: flip `TEMPORAL_ENABLED` and the same interface dispatches to a durable worker.

---

## Key data types

| Type | File | What it is |
|---|---|---|
| `Scenario` | `core/schema.py` | Immutable shelter config: capacity, workforce, intake, cost model, budget |
| `CatIntakeProfile` | `core/schema.py` | Age/health class with arrival weight; all profiles sum to 1.0 |
| `InterventionParams` | `core/interventions.py` | Resource deltas: extra_isolation_slots, extra_vet_tech_fte, extra_foster_slots, adoption_wait_multiplier |
| `SimulationResult` | `core/engine.py` | One replication: intake count, overflow cat-days, cost, utilization per role |
| `MonteCarloSummary` | `core/montecarlo.py` | Across replications: mean, std, 95% CI for overflow and cost |
| `CandidateAllocation` | `optimize/workflow.py` | 4-tuple of budget shares (foster_support, clinic_hours, isolation, adoption_events); sum ≤ 1.0 |
| `EvaluationResult` | `optimize/interface.py` | One candidate outcome: allocation + MonteCarloSummary + feasibility flag |

---

## How to extend

**Add a new optimizer:**
```python
# 1. Implement in optimize/
def my_optimizer(scenario, seed_set, warm_start=None) -> list[CandidateAllocation]:
    ...

# 2. Wire into workflow.py
# Pass your candidates to evaluate_candidate(): do NOT call run_simulation() directly
candidates = my_optimizer(scenario, seed_set, warm_start=baseline_results)
results = [evaluate_candidate(a, scenario, seed_set) for a in candidates]
```

**Add a new API endpoint:**
```python
# In api/app.py
@app.post("/my-endpoint")
def my_endpoint(req: MyRequest) -> MyResponse:
    scenario = _get_scenario()           # demo scenario lazy-loaded from whisker_haven.yaml
    # or:
    scenario = _builder_to_scenario(req) # scenario from 9-field builder form
    ...
```

**Add a new baseline:**
```python
# In optimize/baselines.py
def my_baseline() -> CandidateAllocation:
    return CandidateAllocation(foster=0.5, clinic=0.1, isolation=0.2, adoption=0.2)

# Add to ALL_BASELINES dict in baselines.py
# workflow.py imports ALL_BASELINES and evaluates every entry automatically
```

**Add a new scenario:**
```yaml
# Create scenarios/my_shelter.yaml
# Must pass Scenario.model_validate(yaml.safe_load(path.read_text()))
# Key fields: housing_capacity, isolation_capacity, intake_rate_per_day,
#             workforce (vet_tech, animal_care, foster_coordinator FTE),
#             budget, duration_days, seed
```

---

## Runtime flow: one optimization sweep

```
1. Load scenario
   └─ YAML → yaml.safe_load → Scenario.model_validate → frozen Scenario object

2. Create seed set (CRN)
   └─ montecarlo.make_seed_set(base_seed, n_replications) → list[int]

3. Evaluate baselines
   └─ for each of 5 named allocations in ALL_BASELINES:
       evaluate_candidate(allocation, scenario, seed_set) → EvaluationResult

4. Generate BO candidates
   └─ jaxbo_optimizer.run_bo(scenario, seed_set, warm_start=baseline_results)
      → list[CandidateAllocation] (20 by default)

5. Evaluate BO candidates
   └─ for each candidate:
       evaluate_candidate(allocation, scenario, seed_set) → EvaluationResult
       ├─ resolve_intervention(allocation, scenario) → InterventionParams
       └─ for each seed:
           run_simulation(scenario, seed, intervention) → SimulationResult
       → MonteCarloSummary (mean/std/CI)

6. Rank results
   └─ feasible first (cost ≤ budget), then by overflow_mean ascending

7. Return list[EvaluationResult] to API/CLI
```

---

## Deployment

| | |
|---|---|
| **Image target** | `app` (Dockerfile multi-stage: python + nginx) |
| **Runs** | nginx on :80 serves Next.js static export; uvicorn on :8000 serves FastAPI |
| **Proxy** | nginx forwards `/api/*` to `localhost:8000`: one URL, no CORS |
| **Platform** | AWS ECS Fargate, ECS Express Mode (single consolidated service) |
| **Auto-deploy** | `v*` tag → `deploy.yml` → build image → push to ECR → ECS updates service |
| **Auth** | GitHub OIDC → IAM role (`AWS_ROLE_ARN` secret); no static AWS credentials |
| **Live URL** | https://sh-f52a79071fe149e0ac99448fc11e8496.ecs.us-east-1.on.aws |

---

## Current project status (as of Jun 28 2026)

- **Phases 1–11 complete.** Core sim, BO, API endpoints, UI, ECS deployment all working.
- **Temporal gate (ADR-004, ADR-010):** In-process path chosen. `TEMPORAL_ENABLED = False`. Sweep < 30s: no need for durable workflows.
- **Approaching submission deadline Jul 6–7.**

### Non-negotiables still to close before submission

1. < 5 min demo video with Whisker Haven narrative
2. README a stranger can run from ✓ (done in this overhaul)
3. Aikido scan report in `/security/`
4. `.kiro/` folder committed ✓ (present)
5. Honest baseline comparison for optimizer ✓ (5 baselines in `baselines.py`)

---

## ADR index

| ADR | Decision | Status |
|---|---|---|
| [001](../../docs/adr/001-python-3.12.md) | Python 3.12 | Active |
| [002](../../docs/adr/002-nextjs-react-tailwind.md) | Next.js + React + Tailwind (overrides Streamlit default) | Active |
| [003](../../docs/adr/003-simpy-discrete-event.md) | SimPy for DES | Active |
| [004](../../docs/adr/004-temporal-gate.md) | Gate Temporal to EOD Jun 28 | Active |
| [005](../../docs/adr/005-jaxbo-optimizer.md) | jaxbo as BO plugin | Active |
| [006](../../docs/adr/006-fastapi-rest.md) | FastAPI REST adapter | Active |
| [007](../../docs/adr/007-render-deployment.md) | Render deployment | **Superseded by ADR-011** |
| [008](../../docs/adr/008-aws-app-runner.md) | AWS App Runner | **Superseded by ADR-011** |
| [009](../../docs/adr/009-scipy-gp-optimizer.md) | Real scipy GP+EI optimizer | Active |
| [010](../../docs/adr/010-temporal-gate-result.md) | Temporal gate result: in-process chosen | Active |
| [011](../../docs/adr/011-ecs-express-mode.md) | ECS Express Mode (current deployment) | Active |
