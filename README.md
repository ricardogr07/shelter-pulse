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

_URL added after Phase 3 deployment._

## Scope & future work

See [scope lock](docs/adr/001-python-3.12.md) for what is explicitly deferred:
real shelter-data integrations, multi-shelter networks, advanced UI modes,
Pareto-frontier views, automatic model calibration.

## License

Apache-2.0
