# Worker: API

**Model:** Claude Sonnet 4.6 | **Effort:** medium | **Phase:** 8, 9

**Role:** Maintain and extend `shelterpulse/api/app.py`. File already exists and is
production-ready. Do NOT recreate it.

## Files You Own

- `shelterpulse/api/app.py` (extend only)
- `tests/e2e/test_api.py` (extend only)

Forbidden zones: core/, optimize/ (read-only reference), cli/, ui/, .github/workflows/

## Current Endpoints (DO NOT re-implement)

| Route | Method | Description |
|-------|--------|-------------|
| /health | GET | Returns `{"status": "ok"}` |
| /simulate | POST | Single run via run_simulation() |
| /optimize | POST | Full sweep via run_optimization_sweep() |
| /baselines | GET | 5 named allocations from baselines.py |
| /sensitivity | POST | Tornado chart: 6 perturbations via evaluate_candidate() |
| /simulate/timeline | POST | Daily snapshot data via run_simulation() |
| /simulate/builder | POST | Custom scenario: _builder_to_scenario() + simulate |
| /optimize/builder | POST | Custom scenario: _builder_to_scenario() + sweep |
| /export | POST | export_results() from core/export.py → ZIP |

## How to Add a New Endpoint

1. Define input model (Pydantic, frozen or regular)
2. Define response model (Pydantic)
3. Add thin route function: validate → call into optimize/ or core/ → return response model
4. Use `_get_scenario()` for the demo scenario (Whisker Haven)
5. Use `_builder_to_scenario()` for builder-form inputs
6. No business logic in app.py

## How to Test

```bash
# Start API in one terminal
uv run uvicorn shelterpulse.api.app:app --reload

# Run e2e suite in another
uv run pytest tests/e2e/ -v

# Manual smoke
curl http://localhost:8000/health
curl -X POST http://localhost:8000/optimize \
  -H "Content-Type: application/json" \
  -d '{"n_candidates": 4, "n_reps": 8, "use_bo": false}'
```

## Phase 8 Task (Issue #36)

BO-vs-baselines comparison: the `/optimize` response already returns a ranked
`list[EvaluationResult]` including baselines with `allocation_name` field.
Verify the field is populated for named baselines. If missing, extend the response so
the UI can label rows "Equal Split", "All Foster", etc. Do not change the existing
response structure -- add fields only.

## Phase 9 Tasks (Issues #42, #43)

**Issue #42 (Temporal activation):**
- One-line change: `TEMPORAL_ENABLED = True` in `optimize/workflow.py`
- Wire Temporal worker process in docker-compose.yml (new service)
- Verify sweep still returns ranked results

**Issue #43 (Async /optimize + SSE):**
- POST `/optimize` → returns `{"workflow_id": "<uuid>"}` immediately (non-blocking)
- GET `/optimize/stream?id=<uuid>` → SSE endpoint streaming progress events
- New optional dep: `aio-pika>=9.4` (Orchestrator approval required before adding)

## Key Contracts

- No simulation logic in app.py (all calls go into optimize/ or core/)
- Single evaluation seam: optimizers call `evaluate_candidate()` in interface.py only
- CRN: seed_set fixed at sweep start in workflow.py, same across all candidates
- CORS: `allow_origins` sourced from env var (restrict in prod -- Phase 10 issue #48)
