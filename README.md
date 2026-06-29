# ShelterPulse

> An open-source simulation and optimization laboratory for testing cat-shelter operating policies and resource investments under uncertainty.

ShelterPulse helps cat shelters simulate capacity, understand bottlenecks, and allocate limited resources before operational changes are made in the real world.

## Quick start

### Local (Docker)

```bash
docker compose up
```

- UI: http://localhost:3000
- API: http://localhost:8000/docs

### Local (dev)

```bash
# Python core + API
uv sync
uv run uvicorn shelterpulse.api.app:app --reload

# Next.js UI (separate terminal)
cd ui && npm install && npm run dev
```

## Development

```bash
# Run all checks
uv run tox

# Run tests only
uv run tox -e test

# UI type-check + lint
cd ui && npm run type-check && npm run lint
```

## Project structure

```
shelterpulse/   Python core library (pure — no I/O)
api/            FastAPI REST adapter
cli/            Typer CLI adapter
ui/             Next.js + React + TypeScript + Tailwind frontend
scenarios/      YAML scenario files (Whisker Haven demo)
tests/          pytest unit + e2e suites
docs/           ADRs and architecture diagrams
security/       Aikido scan reports
```

## Live demo

| Service | URL |
|---------|-----|
| App (UI) | https://sh-f52a79071fe149e0ac99448fc11e8496.ecs.us-east-1.on.aws |
| API docs | https://sh-f52a79071fe149e0ac99448fc11e8496.ecs.us-east-1.on.aws/api/docs |

Deployed as a **single consolidated container on AWS ECS Express Mode**: nginx serves the
Next.js static export and reverse-proxies `/api/*` to uvicorn in the same task — one ALB,
one HTTPS URL, no CORS (see [ADR-011](docs/adr/011-ecs-express-mode.md)). A GitHub release
builds the `app` Docker target, pushes it to ECR, and updates the Express service via the
AWS CLI.

## Design decisions

**Simulation:** Discrete-event simulation (SimPy) with non-homogeneous Poisson intake, realistic cat lifecycle (assessment → isolation → medical → housing → foster → adoption), and common random numbers across optimizer candidates for fair comparison.

**Optimization:** Bayesian Optimization via jaxbo with numpy fallback (jax is optional). Random Dirichlet candidates + all named baselines evaluated per sweep.

**Temporal:** Architecture is Temporal-ready — each `evaluate_candidate()` call maps to a Temporal activity. In-process path chosen for hackathon timeline; `TEMPORAL_ENABLED = False` flag can flip it on without touching the optimizer interface.

**No new npm packages:** Chart bars use Tailwind width-percentage `<div>` rather than a chart library — zero build-time dependency risk.

## Scope & future work

See [scope lock](docs/adr/001-python-3.12.md) for what is explicitly deferred:
real shelter-data integrations, multi-shelter networks, advanced UI modes,
Pareto-frontier views, automatic model calibration.

## License

Apache-2.0
