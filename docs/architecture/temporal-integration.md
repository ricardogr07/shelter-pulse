# Temporal Integration Architecture (Phase 5)

How to activate durable optimization sweeps using the Temporal workflow engine.
The `TEMPORAL_ENABLED = False` flag has been in `optimize/workflow.py` since Phase 1.
This document defines what flipping it to `True` requires.

---

## Current state (TEMPORAL_ENABLED = False)

```
API  →  run_optimization_sweep()  →  _inprocess_sweep()
                                       ↳ evaluate_candidate() × N  (sequential, ~30s for N=20)
```

Each candidate is evaluated synchronously. If the API process dies mid-sweep, the sweep
is lost. Adequate for N ≤ 30 and demo use; not adequate for N > 50 or production.

---

## Target state (TEMPORAL_ENABLED = True)

```
API  →  temporal_client.start_workflow(OptimizationSweepWorkflow, params)
                ↓
         Temporal Server (localhost:7233 or managed)
                ↓
         OptimizationSweepWorkflow.run()
           ↓ per candidate
         evaluate_candidate_activity()  ×  N  (parallel Temporal activities)
```

If the API restarts mid-sweep, Temporal replays the workflow from the last checkpoint.
Each activity that already completed is not re-run.

---

## Code changes

### `optimize/workflow.py`

```python
TEMPORAL_ENABLED = True  # flip this flag

async def _temporal_sweep(
    scenario: Scenario,
    seed_set: list[int],
    n_candidates: int,
    use_bo: bool,
) -> list[EvaluationResult]:
    from temporalio.client import Client
    client = await Client.connect(os.getenv("TEMPORAL_ADDRESS", "localhost:7233"))
    handle = await client.start_workflow(
        "OptimizationSweepWorkflow",
        SweepParams(scenario=scenario, seed_set=seed_set, n_candidates=n_candidates, use_bo=use_bo),
        id=f"sweep-{uuid4()}",
        task_queue="shelterpulse-optimizer",
    )
    return await handle.result()
```

### New file: `optimize/temporal_worker.py`

Defines the workflow and activity implementations. Run as a separate process:

```python
@workflow.defn
class OptimizationSweepWorkflow:
    @workflow.run
    async def run(self, params: SweepParams) -> list[EvaluationResult]:
        candidates = generate_candidates(params)
        tasks = [
            workflow.execute_activity(
                evaluate_candidate_activity,
                CandidateInput(allocation=c, scenario=params.scenario, seed_set=params.seed_set),
                start_to_close_timeout=timedelta(minutes=2),
            )
            for c in candidates
        ]
        results = await asyncio.gather(*tasks)
        return sorted(results, key=lambda r: r.mean_overflow_cat_days)

@activity.defn
async def evaluate_candidate_activity(inp: CandidateInput) -> EvaluationResult:
    return evaluate_candidate(inp.allocation, inp.scenario, inp.seed_set)
```

### `docker-compose.yml`

The `temporal` profile stub is already in place. Remove the `profiles: [temporal]` constraint
to include it in the default `docker compose up`:

```yaml
temporal:
  image: temporalio/auto-setup:latest
  ports: ["7233:7233"]
  # profiles: [temporal]  ← remove this line
  environment:
    - DB=sqlite   # dev mode, no external Postgres needed
```

Add the worker service:

```yaml
temporal-worker:
  build: { context: ., target: api }
  command: [".venv/bin/python", "-m", "shelterpulse.optimize.temporal_worker"]
  environment:
    - PYTHONPATH=/app
    - TEMPORAL_ADDRESS=temporal:7233
  depends_on: [temporal]
```

---

## Optional dependency

`temporalio` is already in `pyproject.toml` under `[project.optional-dependencies].temporal`.
Install it: `uv sync --extra temporal`.

---

## SSE progress stream (Phase 5 companion)

While a sweep runs as a Temporal workflow, the API can stream per-candidate progress
via Server-Sent Events:

```
GET /optimize/stream?workflow_id=sweep-abc123
```

Implementation: poll `workflow.history()` every 500ms, emit one SSE event per completed
activity. UI shows a progress bar from 0 → N candidates.

---

## When to activate

Gate criteria (from Phase 5 index):
- Phase 3 (multi-scenario) complete — sweeps now run against multiple scenarios
- Phase 4 Pareto endpoint needs N > 10 sweep points — in-process is too slow
- `uv sync --extra temporal` works in the Docker image
- `temporalio/auto-setup` image is available in the deployment environment

For Render free tier, the Temporal server cannot run alongside the API (memory limit).
Options: managed Temporal Cloud (has free tier), or Railway/Fly.io with more memory.
