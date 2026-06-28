---
inclusion: always
---

# ShelterPulse — Technology Stack

## Python backend (locked)

| Layer | Choice | Notes |
|-------|--------|-------|
| Language | Python 3.12 | Single language for core, API, CLI |
| Simulation | SimPy ≥ 4 | Discrete-event; `simpy.Resource` for queues |
| Schema/validation | Pydantic v2 + PyYAML ≥ 6 | `model_config = ConfigDict(frozen=True, extra="forbid")` pattern |
| REST API | FastAPI ≥ 0.115 + Uvicorn | Auto OpenAPI docs at `/docs` |
| CLI | Typer ≥ 0.12 | Thin declarative wrapper |
| Numerics | NumPy ≥ 2 | Vectorized metrics, RNG via `np.random.default_rng()` |
| Optimizer | jaxbo (Ricardo's JAX-BO fork, Apache-2.0) | Optional dep; scipy fallback if unavailable |
| Packaging | uv + tox + hatchling | `uv run`, `uv sync`, `tox -e test` |
| Dev tools | pytest ≥ 8, pyrefly, bandit | `tox -e lint,security,test,e2e` |

## JavaScript frontend (locked)

| Layer | Choice |
|-------|--------|
| Framework | Next.js (app router) — **read `ui/AGENTS.md` before writing any Next.js code** |
| Language | TypeScript (strict mode on, no `any` without justification) |
| Styling | Tailwind CSS |
| Testing | Cypress (e2e) |

## Infrastructure

| Layer | Choice |
|-------|--------|
| Container | Docker + docker compose |
| Cloud | AWS App Runner + ECR (Free Plan, $200 credits) — see ADR-008 |
| CI | GitHub Actions (`.github/workflows/ci.yml`) |
| CD | Push to GHCR via `.github/workflows/cd.yml` |
| Durable workflow | Temporal (conditional — `TEMPORAL_ENABLED = False` until Jun 28 gate passes) |

## Dependency rules

- **No new pip packages** without orchestrator (Claude) approval. Every new dep = more attack surface + build time.
- `jax` / `jaxlib` stay in `[project.optional-dependencies].optimize` — never move to main deps.
- `temporalio` stays in `[project.optional-dependencies].temporal`.
- **No new npm packages** without approval. Check `package.json` before reaching for a library.

## Test commands

```bash
uv run pytest tests/unit/ -v                         # unit tests
uv run pytest tests/unit/test_conservation.py -v    # regression guard (run after engine changes)
uv run pytest tests/e2e/ -v                         # e2e (needs API running)
cd ui && npm run build                              # Next.js build check
tox -e lint                                         # pyrefly type check
tox -e security                                     # bandit scan
```
