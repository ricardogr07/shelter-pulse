# ShelterPulse

> Simulation and optimization laboratory for cat-shelter resource allocation under uncertainty.

[![CI](https://github.com/ricardogr07/shelter-pulse/actions/workflows/ci.yml/badge.svg)](https://github.com/ricardogr07/shelter-pulse/actions/workflows/ci.yml)
[![Python 3.12](https://img.shields.io/badge/Python-3.12-blue?logo=python&logoColor=white)](https://python.org)
[![SimPy](https://img.shields.io/badge/SimPy-discrete--event-orange)](https://simpy.readthedocs.io/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Next.js-15-black?logo=next.js&logoColor=white)](https://nextjs.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-strict-3178C6?logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-v3-38B2AC?logo=tailwindcss&logoColor=white)](https://tailwindcss.com/)
[![Docker](https://img.shields.io/badge/Docker-multi--stage-2496ED?logo=docker&logoColor=white)](https://www.docker.com/)
[![AWS ECS](https://img.shields.io/badge/AWS_ECS-Express_Mode-FF9900?logo=amazonwebservices&logoColor=white)](https://aws.amazon.com/ecs/)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue)](LICENSE)

---

## The problem

Every spring, kitten season floods cat shelters. Intake surges 2-3x. Isolation queues fill. Housing overflows. Managers face an impossible allocation problem: a fixed budget split across four interventions (foster support, extra clinic hours, temporary isolation capacity, adoption events) with no way to model outcomes before committing real staff and dollars. Gut-feel allocation routinely leaves overflow on the table.

## What we set out to do

Build a simulation and optimization lab that gives shelter managers a fast, honest, reproducible answer to:

> *"Given my shelter's constraints and budget, what allocation minimizes overflow?"*

Requirements: runs in under 5 minutes, compares against honest baselines, quantifies uncertainty, open-source.

## How it works

ShelterPulse stacks four layers:

### Discrete-event simulation (`shelterpulse/core/engine.py`)

SimPy models the complete cat lifecycle: intake assessment, isolation (if needed), medical clearance, housing, foster placement, adoption. Intake follows a non-homogeneous Poisson process with configurable seasonal spikes (kitten season). Each run is fully seeded and reproducible.

### Common Random Numbers (`shelterpulse/core/montecarlo.py`)

Every candidate allocation is evaluated with the *same* seed set across all replications. Without CRN, Monte Carlo variance swamps the allocation signal and you would need ~10x more replications to distinguish two strategies. With CRN, outcome differences are attributable to the allocation, not luck. This is the mathematical foundation that makes the optimizer trustworthy.

### Bayesian Optimization (`shelterpulse/optimize/jaxbo_optimizer.py`)

GP + Expected Improvement (jaxbo primary, scipy fallback) searches the 4-simplex of budget shares. Finds better allocations with fewer function evaluations than random or grid search. All five named baselines (equal split, all-in foster, all-in events, domain heuristic, zero) are evaluated alongside BO candidates for honest comparison.

### Web UI + REST API (`ui/` + `shelterpulse/api/app.py`)

Next.js + Tailwind frontend calling FastAPI. Sensitivity tornado chart, day-by-day housing timeline, ranked optimizer results. Zero chart library dependencies: bars are Tailwind `width: X%` divs.

**Deployment:** nginx + uvicorn in one ECS Fargate task. One ALB, one HTTPS URL, no CORS. Auto-deploys on `v*` tag via GitHub Actions + ECR.

---

## Results

| | |
|---|---|
| **Live app** | https://sh-f52a79071fe149e0ac99448fc11e8496.ecs.us-east-1.on.aws/en |
| **API docs** | https://sh-f52a79071fe149e0ac99448fc11e8496.ecs.us-east-1.on.aws/api/docs |
| **Sweep speed** | 20 candidates x 32 replications in < 30 s |
| **Baselines** | 5 named strategies compared per sweep |
| **Whisker Haven demo** | BO reduces overflow from 234 to 0 cat-days |

---

## Design decisions

Full rationale: [docs/design-decisions.md](docs/design-decisions.md) and [docs/adr/](docs/adr/).

| Decision | Why |
|---|---|
| SimPy for DES | Pure Python, no licenses; single-threaded engine maps naturally to shelter lifecycle |
| Common Random Numbers | Without CRN, replication variance swamps allocation signal |
| GP+EI over random search | Finds better allocations with fewer evaluations; scipy fallback keeps jax optional |
| Consolidated container | One URL for demo; nginx+uvicorn in one ECS task eliminates CORS |
| Temporal deferred | In-process sweep < 30 s; architecture is Temporal-ready via `TEMPORAL_ENABLED` flag |
| Domain heuristic excludes clinic hours | Extra vet FTE worsened overflow in Whisker Haven (creates bottleneck elsewhere) |

---

## Quick start

### One command (Docker)

```bash
docker compose up
```

- UI: http://localhost:3000
- API docs: http://localhost:8000/docs

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

## Project structure

| Path | Purpose |
|---|---|
| `shelterpulse/core/` | Pure library: simulation, Monte Carlo, schema. Zero I/O. |
| `shelterpulse/optimize/` | Sweep orchestrator, Bayesian optimizer, baselines |
| `shelterpulse/api/` | FastAPI REST adapter |
| `shelterpulse/cli/` | Typer CLI adapter |
| `ui/` | Next.js + React + TypeScript + Tailwind |
| `scenarios/` | YAML scenario files (Whisker Haven demo) |
| `docs/` | ADRs + architecture diagrams |
| `security/` | Aikido scan reports |

The core invariant: `shelterpulse/core/` imports nothing from `shelterpulse.api`, `shelterpulse.cli`, or `shelterpulse.optimize`. Enforced by `tests/unit/test_no_cross_imports.py` on every CI run.

See [docs/architecture/](docs/architecture/) for diagrams and [docs/adr/](docs/adr/) for all 11 decision records.

## License

Apache-2.0

## Built with Kiro

This project was developed with [Kiro](https://kiro.dev), an AI-powered development environment.
Kiro assisted across all phases: architecture design, code generation, testing, security patching,
and infrastructure deployment. Every change was verified through CI (pytest + Cypress + tox)
before merging.

Full write-up: [docs/kiro.md](docs/kiro.md)
