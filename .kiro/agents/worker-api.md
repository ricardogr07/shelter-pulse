# Worker: API

**Model:** Claude Sonnet 4.6 | **Effort:** medium

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

Async job dispatch (queue-backed `/optimize/builder` sweeps, webhook completion) is owned by
`worker-queue.md`, not this file -- read that worker's doc before touching anything
queue-related from the API side.

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

## Key Contracts

- No simulation logic in app.py (all calls go into optimize/ or core/)
- Single evaluation seam: optimizers call `evaluate_candidate()` in interface.py only
- CRN: seed_set fixed at sweep start in workflow.py, same across all candidates
- CORS: `allow_origins` sourced from env var; restrict to the actual UI origin in any
  production-facing deployment
