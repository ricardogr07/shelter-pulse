# Module Boundaries

The core architectural constraint: `shelterpulse/core` is a pure library with no I/O.
All adapters (API, CLI, UI) call into it; it never imports from them.

```mermaid
graph TD
    subgraph core["shelterpulse/core  --  pure Python, no I/O"]
        schema["schema.py\nPydantic v2 models + YAML loader\nScenario (frozen) - CatIntakeProfile\nSimulationResult - FosterNetwork"]
        engine["engine.py\nSimPy discrete-event engine\nrun_simulation() - _cat_process()\n_intake_generator() - _metrics_sampler()"]
        interventions["interventions.py\nresolve_intervention()\nbudget shares to InterventionParams\n(resource deltas)"]
        montecarlo["montecarlo.py\nrun_paired() - make_seed_set()\nCRN paired replications to MonteCarloSummary"]
        export_mod["export.py\nexport_results()\nYAML + CSV reproducible output"]

        schema --> engine
        schema --> interventions
        interventions --> montecarlo
        engine --> montecarlo
        montecarlo --> export_mod
    end

    subgraph optimize["shelterpulse/optimize"]
        interface["interface.py\nevaluate_candidate()\nEvaluationResult - CandidateAllocation\n-- THE evaluation seam --"]
        baselines["baselines.py\n5 named allocations:\nequal - all_in_foster - all_in_events\ndomain_heuristic - zero"]
        jaxbo_opt["jaxbo_optimizer.py\nGP+EI (jax primary, scipy fallback)\nsimplex to cube projection"]
        workflow["workflow.py\nrun_optimization_sweep()\nbaselines + BO candidates to ranked list\n(queue abstraction via QUEUE_BACKEND flag)"]

        baselines --> workflow
        jaxbo_opt --> workflow
        interface --> workflow
    end

    subgraph queue["shelterpulse/queue  --  async job dispatch"]
        queue_abs["abstract.py\nQueueBackend ABC\npublish() - consume()"]
        rabbitmq_be["rabbitmq.py\nRabbitMQ adapter (docker-compose)"]
        sqs_be["sqs.py\nSQS adapter (production/Lambda)"]
        worker["worker.py\nConsumes jobs, runs sweep,\ncalls webhook with results"]
        job_store["job_store.py\nDuckDB job persistence"]

        queue_abs --> rabbitmq_be
        queue_abs --> sqs_be
        queue_abs --> worker
    end

    subgraph adapters["Adapters  --  thin I/O wrappers"]
        api_app["api/app.py\nFastAPI:\n/simulate - /optimize - /baselines\n/sensitivity - /simulate/timeline\n/simulate/builder - /optimize/builder\n/export"]
        cli_main["cli/main.py\nTyper commands:\nsimulate - optimize - baselines - export"]
        ui_app["ui/\nNext.js + React + TypeScript\n+ Tailwind CSS\ncalls /api/* via fetch"]
        lambda_fn["lambda/\nAWS Lambda worker\nSQS-triggered BO sweeps"]
    end

    core --> optimize
    core --> api_app
    core --> cli_main
    optimize --> queue
    queue --> adapters
    api_app --> ui_app

    core -. "FORBIDDEN -- enforced by\ntests/unit/test_no_cross_imports.py" .-> adapters

    style core fill:#e8f4e8,stroke:#2d7a2d
    style optimize fill:#e8ecf4,stroke:#2d3d7a
    style queue fill:#f4f0e8,stroke:#7a6d2d
    style adapters fill:#f4ece8,stroke:#7a3d2d
```

## Module map

| Path | Purpose |
|------|---------|
| `shelterpulse/core/` | Pure library: simulation engine, Monte Carlo, schema, interventions. Zero I/O. |
| `shelterpulse/optimize/` | Sweep orchestrator, Bayesian optimizer, baselines, evaluation interface |
| `shelterpulse/queue/` | Async job dispatch: queue abstraction, RabbitMQ/SQS backends, worker, job store |
| `shelterpulse/api/` | FastAPI REST adapter (thin I/O wrapper) |
| `shelterpulse/cli/` | Typer CLI adapter (thin I/O wrapper) |
| `ui/` | Next.js + React + TypeScript + Tailwind CSS frontend |
| `lambda/` | AWS Lambda worker for SQS-triggered BO sweeps |

## The key invariant

```
shelterpulse.core  imports from  nowhere in shelterpulse.*
```

Enforced by `tests/unit/test_no_cross_imports.py` which runs in CI on every PR.

This boundary is what makes the core usable from the API, CLI, and future adapters without circular imports. It also makes the core testable in isolation: no mock of FastAPI or Next.js needed to test the simulation engine.
