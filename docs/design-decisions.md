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

**Decision:** Every allocation is evaluated with the same `seed_set`, pre-generated intake schedule, and per-cat streams separated by stochastic source.

**Why paired streams matter:**

Without CRN, comparing two allocations requires:

```
n_needed ≈ 2 × (z_α/2 + z_β)² × σ² / δ²
```

where `δ` is the true difference and `σ²` is replication variance.

With CRN, the variance of `(overflow_A - overflow_B)` is:

```
Var(X_A - X_B) = Var(X_A) + Var(X_B) - 2·Cov(X_A, X_B)
```

Positive covariance can reduce comparison variance, but reusing only an initial seed is insufficient when intervention-dependent control flow consumes random numbers differently. We therefore pre-generate intake and split per-cat random sources. No ShelterPulse-specific variance-reduction factor is published until it is measured directly.

**Implementation:** `montecarlo.make_seed_set(base_seed, n)` generates the fixed seed list. `engine._generate_arrivals()` creates the exogenous intake schedule before lifecycle execution, and each cat has independent streams for assessment, isolation, clearance, adoption, transfer, and foster coordination.

**Revisit when:** Switching to a variance reduction technique that conflicts with CRN (e.g., antithetic variates across pairs rather than across candidates).

---

## 3. Bayesian Optimization: GP + Expected Improvement

**Decision:** jaxbo (JAX-based GP+EI) is the primary optimizer. If JAX/jaxbo is unavailable, the supported fallback is deterministic seeded Dirichlet random search.

**Why GP+EI over random/grid search:**
- The allocation space is a 4-simplex (shares summing ≤ 1). Random Dirichlet search is unbiased but sample-inefficient: it doesn't use information from prior evaluations.
- GP+EI builds a probabilistic surrogate after each evaluation and uses Expected Improvement to trade off exploration and exploitation.
- Five named baselines warm-start the GP and remain explicitly labeled in the returned ranking. A baseline may outperform every BO candidate.
- A recorded 20-candidate, 32-replication development sweep took 243.2 seconds. Runtime thresholds require repeated final-commit evidence.

**Why jaxbo as primary:**
- jaxbo provides the Matérn-5/2 GP path used by this project.
- Each iteration evaluates Expected Improvement over 256 feasible Dirichlet proposals.

**Fallback boundary:**
- JAX, jaxlib, and jaxbo are optional dependencies.
- Without them, the code does not claim Bayesian optimization; it reports seeded random-search candidates.

**Simplex representation:**
- The GP observes all four spending shares, so zero intervention remains distinct from all-in-events.
- Proposed candidates are sampled on the four-share, full-budget simplex; arbitrary inputs are clipped and normalized only when their sum exceeds one.

**Revisit when:** Sweep time exceeds 5 minutes (async workers already handle this via queue abstraction), or when the allocation space grows beyond 4 interventions (projection changes).

---

## 4. Single evaluation seam: `evaluate_candidate()`

**Decision:** All optimizers: random, grid, JAX-BO: call `interface.evaluate_candidate(allocation, scenario, seed_set)`. No optimizer calls `run_simulation()` directly.

**Why:**
- One place to change replication logic, CRN behavior, cost accumulation
- Makes async dispatch trivial: `evaluate_candidate()` is the natural work unit boundary. The queue abstraction dispatches jobs containing allocations to workers without touching the optimizer interface.
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
- AWS App Runner closed to new customers 2026-04-30 (see [ADR-007](adr/007-ecs-express-mode.md)). ECS Fargate with a load-balanced Express service is the equivalent PaaS path on current AWS.
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

## 7. Queue abstraction: RabbitMQ local, SQS+Lambda prod (retired July 2026)

**Retired:** the entire async path (queue abstraction, RabbitMQ/SQS backends, Lambda worker, job store, SSE progress) was removed in the July 2026 static cutover; `/optimize/builder` is synchronous again. Kept here as the record of the original decision.

**Decision:** Offload BO sweep to background workers via a queue abstraction. `QUEUE_BACKEND` env var selects: sync (default, in-process), rabbitmq (docker-compose), sqs (production).

**Why this architecture:**
- In-process sweep is 30s - acceptable for a blocking request, but poor UX. Async dispatch returns 202 instantly.
- Temporal was evaluated but adds $100/month (Cloud) or complex self-hosting. Our workload is short-lived (~30s) and doesn't need durable replay.
- RabbitMQ locally demonstrates horizontal scaling to judges (`docker compose up --scale worker=4`)
- SQS+Lambda in production costs $0 at the free-tier request/invocation volume (1M requests + 1M invocations/month)

**Feature flag ensures safety:**
- `QUEUE_BACKEND=sync` preserves all existing behavior - CI uses this
- Adding a new backend is one class implementing `QueuePublisher` protocol + factory entry

**Cost caveat discovered post-launch:** the "$0" claim covers SQS + Lambda invocation only. Lambda's webhook callback to the API requires internet egress, and Lambda is VPC-attached (for its EFS/DuckDB mount), so real internet access needs a NAT Gateway (~$32-35/month) — the one component of this design that isn't actually free. See [ADR-010](adr/010-async-worker-production-hardening.md).

**Revisit when:** Workload requires durable multi-step workflows (retry, compensation, human-in-the-loop approval), or sweep time exceeds Lambda's 15-min timeout.

---

## 8. No chart library in UI

**Decision:** Bar charts are Tailwind `width: X%` `<div>` elements. No recharts, no chart.js, no d3.

**Why:**
- Every npm dependency is a build-time risk surface: breaking change, CVE, peer-dep conflict, bundle bloat.
- The optimizer results table only needs horizontal bars sized proportionally to overflow values. That's 3 lines of TSX + 1 Tailwind class.
- Zero build-time dependency risk, zero bundle impact.

**Ceiling:** No tooltips on hover, no animated transitions, no axis labels, no log scale. Acceptable for the current scope; recharts is the obvious add if advanced analytics visualization is needed.

---

## 9. Domain heuristic excludes clinic hours

**Decision:** The `domain_heuristic` baseline in `baselines.py` allocates 40% foster + 20% isolation + 40% adoption events. Clinic hours (extra vet-tech FTE) receive 0%.

**Why:**
- During testing on the Whisker Haven scenario, adding vet-tech FTE *increased* overflow. The bottleneck was housing capacity, not medical clearance throughput: extra vet-techs cleared cats faster but housing was already saturated, so faster-cleared cats joined a longer housing queue.
- This is scenario-specific but illustrative: the right allocation depends on which resource is the binding constraint. Clinic hours only help when medical clearance is the bottleneck.

**Documented in:** `shelterpulse/optimize/baselines.py` comment on `domain_heuristic`.
