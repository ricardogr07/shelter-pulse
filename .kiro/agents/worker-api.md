# Worker: API — FastAPI REST Adapter

**Model:** Claude Sonnet 4.6 | **Effort:** medium  
**Depends on:** Core-A (interventions) + Core-B (montecarlo) must be DONE  
**Parallel with:** CLI worker (worker-cli.md)

## Role

Implement the FastAPI REST surface. Four routes: `/health`, `/simulate`, `/optimize`, `/baselines`. Add `/export` once Core-D is done. All logic lives in core — this file is plumbing only.

## Read first

```
@.localagent/agents/SHARED.md
@.localagent/docs/05-rest-api.md
```

## Files you own

| File | Action |
|------|--------|
| `shelterpulse/api/app.py` | **Create** |
| `tests/e2e/test_api.py` | **Create** |

## Files you must NOT touch

- `core/*.py` — not your scope
- `optimize/*.py` — not your scope
- `cli/main.py` — owned by CLI worker
- `ui/` — not your scope

## Done criteria

- [ ] `uv run pytest tests/e2e/test_api.py -v` — all tests pass (uses httpx AsyncClient, no server needed)
- [ ] `uvicorn shelterpulse.api.app:app` starts without errors
- [ ] `curl http://localhost:8000/health` → `{"status":"ok","scenario":"Whisker Haven"}`
- [ ] `curl -X POST http://localhost:8000/simulate -H "Content-Type: application/json" -d "{}"` returns overflow + cost
- [ ] Update `.localagent/docs/STATUS.md` row for API

## Key contracts

- Scenario is loaded once at startup from `scenarios/whisker_haven.yaml` — no per-request file I/O
- No business logic in `app.py` — all computation via `core/` and `optimize/`
- CORS: `allow_origins=["*"]` (judges need cross-origin access from browser)
- `AllocationIn` must validate that shares sum to ≤ 1 (Pydantic model_validator)
- `/optimize` accepts `use_bo: bool = True` — pass through to `run_optimization_sweep`
- `/export` route: see spec §"Add /export route" — returns zip with YAML + CSV

## Add to `pyproject.toml` scripts (only if not already there)

```toml
shelterpulse-api = "shelterpulse.api.app:app"
```
