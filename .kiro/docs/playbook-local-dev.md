# Playbook: Local Development Modes

Run ShelterPulse locally in any combination. Pick the mode that fits your workflow.

---

## Mode A: Full Docker (split services)

Best for: quick verification, no local deps needed.

```bash
docker compose up --build
```

| Service | Port | URL |
|---------|------|-----|
| API | 8000 | http://localhost:8000/health |
| UI | 3000 | http://localhost:3000/en |

Stop: `docker compose down`

Notes:
- UI is a static export served by nginx (no hot reload)
- API changes require `docker compose up --build api`

---

## Mode B: Full Native

Best for: active development on both API and UI with hot reload.

```bash
# Terminal 1: API
uv run uvicorn shelterpulse.api.app:app --reload --port 8000

# Terminal 2: UI
cd ui && npm run dev
```

| Service | Port | URL |
|---------|------|-----|
| API | 8000 | http://localhost:8000/health |
| UI | 3000 | http://localhost:3000/en |

Notes:
- Both have hot reload
- UI calls API at `http://localhost:8000` (hardcoded default in `ui/src/api.ts`)
- Python deps: `uv sync --all-groups`
- Node deps: `cd ui && npm ci`

---

## Mode C: Hybrid (container API + native UI)

Best for: frontend work with hot reload, backend stable in container.

```bash
# Terminal 1: API in Docker
docker compose up --build api

# Terminal 2: UI native (hot reload)
cd ui && npm run dev
```

| Service | Port | URL |
|---------|------|-----|
| API | 8000 | http://localhost:8000/health |
| UI | 3000 | http://localhost:3000/en |

Notes:
- Frontend hot reloads instantly, backend is the exact container image
- Good for testing UI changes against the production-like API

---

## Mode D: Consolidated Container (ECS simulation)

Best for: pre-deploy verification. Simulates exactly what ECS runs.

```bash
# Build the consolidated image
docker build --target app -t shelterpulse:local --build-arg NEXT_PUBLIC_API_URL=/api .

# Run it
docker run --rm -p 8080:8080 --name sp-local shelterpulse:local
```

| Service | Port | URL |
|---------|------|-----|
| Everything | 8080 | http://localhost:8080/en |
| API (proxied) | 8080 | http://localhost:8080/api/health |

Stop: `docker stop sp-local`

Notes:
- Single container: nginx (8080) proxies `/api/*` to uvicorn (internal 8000)
- This is what runs in ECS Express Mode
- UI is static (no hot reload) -- this is a verification step, not a dev mode
- Run `scripts/smoke_test.py` against this to gate before PR

---

## Smoke Test Gate

After starting any mode, run the smoke test to verify everything works:

```bash
# Quick (health checks only, < 5s)
uv run python scripts/smoke_test.py --quick

# Full (functional API + UI route checks)
uv run python scripts/smoke_test.py
```

The script auto-detects which ports are active and tests accordingly.

---

## Environment Variables

| Variable | Where | Default | Purpose |
|----------|-------|---------|---------|
| `NEXT_PUBLIC_API_URL` | UI build-time | `http://localhost:8000` | API base URL baked into static export |
| `PYTHONUNBUFFERED` | API container | `1` | Flush logs immediately |

For Mode D, `NEXT_PUBLIC_API_URL=/api` so the browser uses relative paths (same-origin, no CORS).

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Port 8000 already in use | `lsof -i :8000` (Linux/Mac) or `netstat -ano \| findstr :8000` (Windows) |
| Stale Docker image | `docker compose build --no-cache` |
| UI shows old content after API change | Rebuild: `docker compose up --build` |
| CORS errors in browser | You're hitting a different origin. Use Mode D or ensure API URL matches |
| nginx permission denied (Mode D) | Container runs as non-root; ensure port is 8080 not 80 |
