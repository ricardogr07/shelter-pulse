# Docker Local Testing

All infrastructure changes must be verified locally before pushing.

## Quick Start

```bash
docker compose up --build -d
```

This starts 2 services:
- **api** (port 8000): FastAPI; optimization sweeps run synchronously in-process
- **ui** (port 3000): Next.js static export via nginx

## Verify Health

```bash
curl http://localhost:8000/health
# {"status":"ok","scenario":"Whisker Haven"}

curl http://localhost:3000/en
# HTML response
```

## Test an Optimization Sweep

```bash
# Blocks until the sweep completes (~30s), returns the ranked results directly
curl -X POST http://localhost:8000/optimize/builder \
  -H 'Content-Type: application/json' \
  -d '{"duration_days":30,"housing_capacity":20,"n_replications":4}'
# Returns: [{...}, ...]
```

## Running Tests

```bash
uv run pytest tests/unit/ tests/e2e/ -v
```

## Troubleshooting

### API returning 500 on /optimize/builder
Check API logs: `docker logs shelter-pulse-api-1 --tail 30`

### Stale images
```bash
docker compose down
docker compose up --build -d
```
