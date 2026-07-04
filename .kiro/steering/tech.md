---
inclusion: always
---

# ShelterPulse: Technology Stack

## Python backend (locked)

| Layer | Choice | Notes |
|-------|--------|-------|
| Language | Python 3.12 | Single language for core, API, CLI |
| Simulation | SimPy ≥ 4 | Discrete-event; `simpy.Resource` for queues |
| Schema/validation | Pydantic v2 + PyYAML ≥ 6 | `model_config = ConfigDict(frozen=True, extra="forbid")` pattern |
| REST API | FastAPI ≥ 0.115 + Uvicorn | Auto OpenAPI docs at `/docs` |
| CLI | Typer ≥ 0.12 | Thin declarative wrapper |
| Numerics | NumPy ≥ 2 | Vectorized metrics, RNG via `np.random.default_rng()` |
| Optimizer | jaxbo (fork of JAX-BO, Apache-2.0) | Optional dep; scipy fallback if unavailable |
| Packaging | uv + tox + hatchling | `uv run`, `uv sync`, `tox -e test` |
| Dev tools | pytest ≥ 8, pyrefly, bandit | `tox -e lint,security,test,e2e` |

## JavaScript frontend (locked)

| Layer | Choice |
|-------|--------|
| Framework | Next.js (app router): **read `ui/AGENTS.md` before writing any Next.js code** |
| Language | TypeScript (strict mode on, no `any` without justification) |
| Styling | Tailwind CSS |
| Testing | Cypress (e2e) |

## Infrastructure

| Layer | Choice |
|-------|--------|
| Container | Docker + docker compose |
| Cloud | **AWS ECS Express Mode + ECR** -- single consolidated container (nginx + uvicorn), one ALB, one HTTPS URL. See ADR-007. |
| CI | GitHub Actions (`.github/workflows/ci.yml`, `promote.yml`, `auto-release.yml`, `deploy.yml`; `release.yml` is a manual hotfix escape hatch). See `.github/workflows.md`. |
| CD | Push to `main` triggers `auto-release.yml` (semver bump from conventional commits) → `deploy.yml`: build + push `app` target to ECR, ECS auto-deploys |
| Async workers | Queue abstraction (ADR-008). `QUEUE_BACKEND=sync\|rabbitmq\|sqs`. RabbitMQ local, SQS+Lambda prod. |

## Dependency rules

- **No new pip packages** without orchestrator (Claude) approval. Every new dep = more attack surface + build time.
- `jax` / `jaxlib` stay in `[project.optional-dependencies].optimize`: never move to main deps.
- `aio-pika` in `[project.optional-dependencies].worker` for RabbitMQ backend.
- `boto3` in `[project.optional-dependencies].aws` for SQS backend.
- **No new npm packages** without approval. Check `package.json` before reaching for a library.

## Test commands

Canonical invocation is `tox`; it isolates the environment. Direct `uv run pytest` works for a fast local loop but bypasses that isolation.

```bash
tox -e lint                                          # pyrefly type check
tox -e security                                      # bandit scan
tox -e test                                          # unit tests + coverage
tox -e e2e                                           # e2e (spins up services as needed)
tox -e whitepaper                                    # builds docs/whitepaper/shelterpulse-whitepaper.pdf
uv run pytest tests/unit/test_conservation.py -v    # regression guard, run after any engine change
cd ui && npm run type-check && npm run lint && npm run build
```
