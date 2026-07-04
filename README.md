# ShelterPulse

> Simulation and optimization laboratory for cat-shelter resource allocation under uncertainty.

[![CI](https://github.com/ricardogr07/shelter-pulse/actions/workflows/ci.yml/badge.svg)](https://github.com/ricardogr07/shelter-pulse/actions/workflows/ci.yml)
[![Python 3.12](https://img.shields.io/badge/Python-3.12-blue?logo=python&logoColor=white)](https://python.org)
[![SimPy](https://img.shields.io/badge/SimPy-discrete--event-orange)](https://simpy.readthedocs.io/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Next.js-16-black?logo=next.js&logoColor=white)](https://nextjs.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-strict-3178C6?logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-v3-38B2AC?logo=tailwindcss&logoColor=white)](https://tailwindcss.com/)
[![Docker](https://img.shields.io/badge/Docker-multi--stage-2496ED?logo=docker&logoColor=white)](https://www.docker.com/)
[![AWS ECS](https://img.shields.io/badge/AWS_ECS-Express_Mode-FF9900?logo=amazonwebservices&logoColor=white)](https://aws.amazon.com/ecs/)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue)](LICENSE)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.21173654.svg)](https://doi.org/10.5281/zenodo.21173654)

---

## The problem

Every spring, kitten season floods cat shelters. Intake surges 2-3x. Isolation queues fill. Housing overflows. Managers face an impossible allocation problem: a fixed budget split across four interventions (foster support, extra clinic hours, temporary isolation capacity, adoption events) with no way to model outcomes before committing real staff and dollars. Gut-feel allocation routinely leaves overflow on the table.

Every overflow cat-day is not an abstract number: it is a cat waiting in a temporary spot, a shelter running above safe density, a longer stay that raises infection-control risk (URI, ringworm), and staff time absorbed that could go to intake or adoption counseling instead. Fewer overflow cat-days means fewer of these difficult capacity decisions during the exact weeks intake is hardest to keep up with. That is the mechanism the metric stands in for, not a claim that this synthetic model has measured real-world welfare outcomes.

## What we set out to do

Build a simulation and optimization lab that gives shelter managers a fast, honest, reproducible answer to:

> *"Given my shelter's constraints and budget, what allocation minimizes overflow?"*

Requirements: runs in under 5 minutes, compares against honest baselines, quantifies uncertainty, open-source.

## How it works

![How it works: Browser (Next.js UI) calls nginx over HTTPS, which proxies /api/* to FastAPI (sync). FastAPI calls shelterpulse/core directly for the request-response path, and separately enqueues BO sweeps to RabbitMQ (local) / SQS (prod), which dispatches to a RabbitMQ worker (local) / Lambda (prod) - the worker reuses the same core simulation code and calls back to FastAPI via a webhook, which streams SSE progress back to the browser.](docs/images/readme-how-it-works.svg)

ShelterPulse stacks four layers:

### Discrete-event simulation

SimPy models the complete cat lifecycle: intake assessment, isolation (if needed), medical clearance, housing, foster placement, adoption. Intake follows a non-homogeneous Poisson process with configurable seasonal spikes (kitten season). Each run is fully seeded and reproducible.

### Common Random Numbers

Every allocation is evaluated with the same seed set, a pre-generated intake schedule, and per-cat random streams separated by stochastic source. This paired-seed design aligns exogenous variation across allocations. ShelterPulse does not publish a numerical variance-reduction factor without a dedicated measurement study.

### Bayesian Optimization

GP + Expected Improvement searches the budget-share simplex when JAX/`jaxbo` is installed; a deterministic Dirichlet random search is the fallback. All five named baselines (equal split, all-in foster, all-in events, domain heuristic, zero) are evaluated and labeled alongside candidates. A baseline may win the sweep.

### Web UI + REST API

Next.js + Tailwind frontend calling FastAPI. Sensitivity tornado chart, day-by-day housing timeline, ranked optimizer results. Zero chart library dependencies: bars are Tailwind `width: X%` divs.

**Deployment:** nginx + uvicorn in one ECS Fargate task. One ALB, one HTTPS URL, no CORS. Pushing to `main` triggers an automatic semver release (GitHub Actions) that tags, builds, and deploys via ECR - no manual tagging.

**Async workers:** BO sweeps dispatch to background workers via a queue abstraction. RabbitMQ in docker-compose (horizontal scaling demo), SQS+Lambda in production. Feature flag `QUEUE_BACKEND` selects the backend. In-memory job state self-heals: jobs stuck for 5 minutes are TTL-expired so the UI never hangs forever on a lost worker callback.

---

## Results

| | |
|---|---|
| **Live app** | https://shelter-pulse.com/en |
| **API docs** | https://shelter-pulse.com/api/docs |
| **Measured sweep** | 5 baselines + 20 BO candidates x 32 replications in 243.2 s on the recorded development environment |
| **Baselines** | 5 named strategies compared per sweep |
| **Whisker Haven evidence** | All-events baseline: 50.2 mean overflow cat-days; best BO candidate: 82.1; equal allocation: 874.4 |

**The most surprising modeling result:** of the four intervention levers, only `adoption_events` changes cats' *rate of leaving* the shelter; foster support, extra clinic hours, and temporary isolation only add capacity or speed up processing upstream of that exit. Under this model, that is why concentrating budget on adoption events consistently outperforms every other allocation this project tested, including what Bayesian optimization finds - a structural property of the levers, not a search failure. Full mechanism, a multi-objective search that confirms it, and the honest negative result for BO: [whitepaper](docs/whitepaper/whitepaper.md).

These are synthetic, model-dependent development results. Configuration, seeds, source digests, confidence intervals, and the complete ranking are retained in [`docs/whitepaper/evidence/whisker-haven.json`](docs/whitepaper/evidence/whisker-haven.json). Regenerate the artifact on the final release commit before quoting it externally.

**For shelters considering this model operationally:** every intake rate, service-time distribution, intervention effect, and cost figure here is a synthetic assumption, not measured from your shelter's records. Treat these results as a demonstration of the method, not a ready-to-use recommendation, until local data replaces the assumptions - see the whitepaper's [Limitations and Conclusions](docs/whitepaper/whitepaper.md) for the specific gaps (no isolation-queue metric, no euthanasia outcome, synthetic-only calibration) and what real-data validation would require.

---

## Design decisions

Full rationale: [docs/design-decisions.md](docs/design-decisions.md) and [docs/adr/](docs/adr/).

| Decision | Why |
|---|---|
| SimPy for DES | Pure Python, no licenses; single-threaded engine maps naturally to shelter lifecycle |
| Paired random streams | Align intake and per-cat random sources across allocation comparisons |
| GP+EI with honest fallback | JAX/`jaxbo` path uses GP+EI; missing optional dependencies fall back to seeded random search |
| Consolidated container | One URL for demo; nginx+uvicorn in one ECS task eliminates CORS |
| RabbitMQ local, SQS+Lambda prod | Keeps local and production queue adapters explicit without claiming proven automatic retry |
| DuckDB over ClickHouse | Embedded run analytics without a separate database server; persistence limits are documented |
| Named domain heuristic | Retained as a transparent comparator, not assumed to outperform simpler baselines |

---

## Quick start

### One command (Docker)

```bash
docker compose up
```

- UI: http://localhost:3000
- API docs: http://localhost:8000/docs
- RabbitMQ management: http://localhost:15672 (shelter/pulse)

This starts 4 services: API (async mode), UI, RabbitMQ, and a background worker.

### Dev mode

```bash
# Python core + API
uv sync
uv run uvicorn shelterpulse.api.app:app --reload

# Next.js UI (separate terminal)
cd ui && npm install && npm run dev
```

## Run checks

```bash
uv run tox                                    # all checks (lint + security + tests)
uv run tox -e test                            # tests only
cd ui && npm run type-check && npm run lint   # frontend
```

## Test suite

| Suite | Tool | Scope | Status |
|-------|------|-------|--------|
| Unit tests | pytest | 133 collected tests | Run by `tox -e test` |
| E2E API tests | pytest + httpx | API contracts | Run by `tox -e e2e` |
| Integration tests | pytest + docker | Queue/worker lifecycle | Separate Docker gate |
| UI smoke tests | Cypress | Static and production-only specs | UI/deploy gates |
| Type checking | TypeScript tsc | - | ✅ No errors |
| Lint (Python) | pyrefly | - | ✅ Clean |
| Lint (JS/TS) | ESLint | - | ✅ Clean |
| Security | Bandit | - | ✅ No findings |
| Coverage | pytest-cov | 73% of `shelterpulse/` (`tox -e test`) | Evidence gate |

GitHub Actions selects the relevant Python, UI, and Docker checks from changed paths on pull requests targeting `develop`.

## Project structure

| Path | Purpose |
|---|---|
| `shelterpulse/core/` | Pure library: simulation, Monte Carlo, schema. Zero I/O. |
| `shelterpulse/optimize/` | Sweep orchestrator, Bayesian optimizer, baselines |
| `shelterpulse/queue/` | Async job dispatch: queue abstraction, RabbitMQ/SQS backends, worker, in-memory job store |
| `shelterpulse/store/` | Optional DuckDB persistence (run history, consent log, analytics) |
| `shelterpulse/api/` | FastAPI REST adapter |
| `shelterpulse/cli/` | Typer CLI adapter |
| `lambda/` | AWS Lambda worker (lean container image for SQS-triggered BO sweeps) |
| `ui/` | Next.js + React + TypeScript + Tailwind |
| `scenarios/` | YAML scenario files (Whisker Haven demo) |
| `docs/` | ADRs + architecture diagrams |
| `security/` | Aikido scan reports |

The core invariant: `shelterpulse/core/` imports nothing from `shelterpulse.api` or `shelterpulse.cli`. Enforced by `tests/unit/test_no_cross_imports.py` on every CI run.

See [docs/architecture/](docs/architecture/) for diagrams and [docs/adr/](docs/adr/) for all 10 decision records.

## Scope and future work

ShelterPulse today is a synthetic decision-support prototype validated for reproducibility and honest baseline comparison, not for operational deployment. The full account of what is proven versus assumed, and the concrete path toward real-data calibration, is in the whitepaper's [Limitations and Future Work](docs/whitepaper/whitepaper.md) sections.

## License

Apache-2.0

## Built with Kiro

This project was developed with [Kiro](https://kiro.dev), an AI-powered development environment.
Kiro assisted across all phases: architecture design, code generation, testing, security patching,
and infrastructure deployment. Every change was verified through CI (pytest + Cypress + tox)
before merging.

Full write-up: [docs/kiro.md](docs/kiro.md)
