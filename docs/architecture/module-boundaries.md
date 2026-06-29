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
        workflow["workflow.py\nrun_optimization_sweep()\nbaselines + BO candidates to ranked list\n(TEMPORAL_ENABLED = False)"]

        baselines --> workflow
        jaxbo_opt --> workflow
        interface --> workflow
    end

    subgraph adapters["Adapters  --  thin I/O wrappers"]
        api_app["api/app.py\nFastAPI:\n/simulate - /optimize - /baselines\n/sensitivity - /simulate/timeline\n/simulate/builder - /optimize/builder\n/export"]
        cli_main["cli/main.py\nTyper commands:\nsimulate - optimize - baselines - export"]
        ui_app["ui/\nNext.js + React + TypeScript\n+ Tailwind CSS\ncalls /api/* via fetch"]
    end

    core --> optimize
    core --> api_app
    core --> cli_main
    api_app --> ui_app

    core -. "FORBIDDEN -- enforced by\ntests/unit/test_no_cross_imports.py" .-> adapters

    style core fill:#e8f4e8,stroke:#2d7a2d
    style optimize fill:#e8ecf4,stroke:#2d3d7a
    style adapters fill:#f4ece8,stroke:#7a3d2d
```

## The key invariant

```
shelterpulse.core  imports from  nowhere in shelterpulse.*
```

Enforced by `tests/unit/test_no_cross_imports.py` which runs in CI on every PR.

This boundary is what makes the core usable from the API, CLI, and future adapters without circular imports. It also makes the core testable in isolation: no mock of FastAPI or Next.js needed to test the simulation engine.
