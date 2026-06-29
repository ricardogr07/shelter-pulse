# Design Decisions

Consolidated rationale for non-obvious choices in ShelterPulse. Each section covers the decision, why it was made, and what would trigger revisiting it. See [docs/adr/](adr/) for the formal ADR trail.

---

## 1. Simulation engine: SimPy discrete-event simulation

**Decision:** SimPy 4 as the DES engine over alternatives (AnyLogic, Mesa, custom event loop).

**Why SimPy:**
- Pure Python: no licenses, no binary dependencies, runs anywhere Python does
- `simpy.Resource` maps directly to shelter resources: housing slots, isolation slots, vet-tech FTE, foster coordinator slots
- Single-threaded per `simpy.Environment`: deterministic given the same seed, no thread-safety surface
- Parallelism happens at the replication level (different seeds), not inside one run

**Why non-homogeneous Poisson intake:**
- Shelter intake is not time-homogeneous: kitten season creates 2–3× surges
- `SeasonalEvent` in the schema lets the scenario define multiplier windows; the engine applies them to the base arrival rate
- Realistic intake shape changes which interventions help most (isolation capacity matters more during surge)

**Revisit when:** The shelter lifecycle needs true agent-level state (cat memory across visits, re-intake tracking). SimPy's process model handles this but becomes verbose.

---

## 2. Common Random Numbers (CRN)

**Decision:** Every candidate allocation is evaluated with the same `seed_set`. The set is fixed before the sweep and passed unchanged to every `evaluate_candidate()` call.

**Why CRN is non-negotiable:**

Without CRN, comparing two allocations requires:

```
n_needed ≈ 2 × (z_α/2 + z_β)² × σ² / δ²
```

where `δ` is the true difference and `σ²` is replication variance. In practice, replication variance in the Whisker Haven scenario is large enough that without CRN you need ~10× more replications to achieve the same statistical power to detect a given allocation difference.

With CRN, the variance of `(overflow_A - overflow_B)` is:

```
Var(X_A - X_B) = Var(X_A) + Var(X_B) - 2·Cov(X_A, X_B)
```

Positive covariance from shared seeds reduces this substantially: same-seed runs covary because they see the same arrival sequence, so allocation differences dominate.

**Implementation:** `montecarlo.make_seed_set(base_seed, n)` generates the fixed seed list. `workflow.py` calls `run_optimization_sweep(scenario, seed_set=seed_set)` once and passes the same seed_set to every candidate. Breaking this (using fresh seeds per candidate) silently invalidates the ranking.

**Revisit when:** Switching to a variance reduction technique that conflicts with CRN (e.g., antithetic variates across pairs rather than across candidates).

---

## 3. Bayesian Optimization: GP + Expected Improvement

**Decision:** jaxbo (JAX-based GP+EI) as primary optimizer, scipy GP+EI as fallback, random Dirichlet as final fallback.

**Why GP+EI over random/grid search:**
- The allocation space is a 4-simplex (shares summing ≤ 1). Random Dirichlet search is unbiased but sample-inefficient: it doesn't use information from prior evaluations.
- GP+EI builds a probabilistic surrogate after each evaluation and maximizes Expected Improvement: trading off exploration (high uncertainty) vs. exploitation (near observed minima). This finds better allocations with fewer function evaluations.
- 20 candidates evaluated with 32 replications each takes < 30s in-process. BO vs. random makes a measurable difference even at this scale.

**Why jaxbo as primary:**
- jaxbo is Ricardo's own Apache-2.0 JAX-BO implementation: zero third-party trust risk, full control over the GP kernel (Matern-5/2) and acquisition function
- JAX enables GPU acceleration for free if the runtime has a GPU

**Why scipy fallback:**
- jax + jaxlib add ~200 MB to the Docker image. In `[project.optional-dependencies].optimize`, they're optional.
- scipy GP+EI (via `scipy.optimize.minimize` + numpy linear algebra) covers the same interface with no extra dependencies.

**4-simplex → 3-cube projection:**
- BO works in [0,1]³ (3-dimensional unit cube). The 4-simplex (4 shares summing to 1) is represented by dropping one coordinate and normalizing via softmax. The optimizer sees a 3-cube; the evaluation layer reconstructs 4 shares. See `jaxbo_optimizer.py`.

**Revisit when:** Sweep time exceeds 5 minutes (add Temporal for async worker offload), or when the allocation space grows beyond 4 interventions (projection changes).

---

## 4. Single evaluation seam: `evaluate_candidate()`

**Decision:** All optimizers: random, grid, JAX-BO: call `interface.evaluate_candidate(allocation, scenario, seed_set)`. No optimizer calls `run_simulation()` directly.

**Why:**
- One place to change replication logic, CRN behavior, cost accumulation
- Makes Temporal adoption trivial: `evaluate_candidate()` maps 1:1 to a Temporal activity. Flip `TEMPORAL_ENABLED` and the same interface dispatches to a durable worker.
- Prevents copy-paste drift where two optimizers accidentally use different seed strategies

**Implementation:** `shelterpulse/optimize/interface.py`: `EvaluationResult` carries mean/std/95% CI for both overflow and cost.

---

## 5. Frozen Pydantic models

**Decision:** `Scenario` and `InterventionParams` are `ConfigDict(frozen=True)`.

**Why:**
- A simulation sweep evaluates many candidates against the same scenario. If `Scenario` were mutable, an optimizer or intervention function could accidentally modify shared state between replications.
- Frozen models are hashable: can be used as dict keys or set members without copying.
- Pydantic raises `ValidationError` on any attempted mutation, surfacing bugs immediately rather than at assertion time.

**Consequence:** Adding fields to `Scenario` requires `Scenario.model_copy(update={"field": value})` not attribute assignment.

---

## 6. ECS Express Mode: consolidated container

**Decision:** Single Docker image (`app` target in `Dockerfile`) runs nginx + uvicorn in one ECS Fargate task. Nginx serves the Next.js static export and reverse-proxies `/api/*` to uvicorn. One ALB, one HTTPS URL.

**Why:**
- Demo needs one URL. Two separate services (UI + API) require CORS headers, two ALBs, two service URLs: complexity with no benefit for a hackathon demo.
- AWS App Runner closed to new customers 2026-04-30 (see ADR-008). ECS Fargate with a load-balanced Express service is the equivalent PaaS path on current AWS.
- Consolidated image eliminates the `NEXT_PUBLIC_API_URL` bake-at-build-time problem: the UI's `/api/*` calls go to the same origin, so no CORS and no build-time env var needed.

**What the Dockerfile does:**
```
api target   → python:3.12-slim + uv + uvicorn on :8000
ui-build     → node:20 + npm ci + next build (static export to /out)
app target   → python:3.12-slim + nginx:alpine + /out + nginx.conf
               nginx serves /out on :80, proxies /api/* to :8000
```

**Revisit when:** UI needs server-side rendering (currently `output: "export"` is static). At that point, split into two services with proper CORS.

---

## 7. Temporal deferred

**Decision:** `TEMPORAL_ENABLED = False`. The in-process sweep completes in < 30s for 20 candidates × 32 replications. Temporal not adopted.

**Why deferral was correct:**
- In-process is fast enough. Temporal adds: a Temporal server dependency, worker process management, retry/timeout configuration, serialization of `Scenario` and `seed_set` over the task queue. None of that is free.
- EOD Jun 28 gate (ADR-004): core sim + BO running end-to-end → adopt Temporal. Gate passed but the timing advantage didn't justify the operational cost (ADR-010).

**Architecture is Temporal-ready:**
- `evaluate_candidate()` in `interface.py` is the natural activity boundary
- `workflow.py` has the `TEMPORAL_ENABLED` flag and the stub orchestration path
- Flipping the flag routes sweep execution through `temporalio.workflow` without touching the optimizer interface

**Revisit when:** Sweep time exceeds 2 minutes, or the shelter wants multi-shelter concurrent sweeps that saturate a single process.

---

## 8. No chart library in UI

**Decision:** Bar charts are Tailwind `width: X%` `<div>` elements. No recharts, no chart.js, no d3.

**Why:**
- Every npm dependency is a build-time risk surface: breaking change, CVE, peer-dep conflict, bundle bloat.
- The optimizer results table only needs horizontal bars sized proportionally to overflow values. That's 3 lines of TSX + 1 Tailwind class.
- Zero build-time dependency risk, zero bundle impact.

**Ceiling:** No tooltips on hover, no animated transitions, no axis labels, no log scale. Acceptable for hackathon demo; recharts is the obvious add for Phase 4 analytics.

---

## 9. Domain heuristic excludes clinic hours

**Decision:** The `domain_heuristic` baseline in `baselines.py` allocates 40% foster + 20% isolation + 40% adoption events. Clinic hours (extra vet-tech FTE) receive 0%.

**Why:**
- During testing on the Whisker Haven scenario, adding vet-tech FTE *increased* overflow. The bottleneck was housing capacity, not medical clearance throughput: extra vet-techs cleared cats faster but housing was already saturated, so faster-cleared cats joined a longer housing queue.
- This is scenario-specific but illustrative: the right allocation depends on which resource is the binding constraint. Clinic hours only help when medical clearance is the bottleneck.

**Documented in:** `shelterpulse/optimize/baselines.py` comment on `domain_heuristic`.
