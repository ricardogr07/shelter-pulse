# Module Boundaries

The core architectural constraint: `shelterpulse/core` is a pure library with no I/O.
All adapters (API, CLI, UI) call into it; it never imports from them.

```mermaid
graph TD
  subgraph core["shelterpulse/core  —  pure Python, no I/O"]
    schema["schema.py\nPydantic models + YAML loader"]
    entities["entities.py\nArea · ProcessStage · WorkforcePool\nFosterNetwork · CatProfile"]
    events["events.py\nOperational / shock / intervention events"]
    engine["engine.py\nSimPy discrete-event engine"]
    metrics["metrics.py\nFlow · capacity · workforce · financial · uncertainty"]
    interventions["interventions.py\nIntervention contracts + dollar→resource adapters"]
    montecarlo["montecarlo.py\nPaired replications · common random numbers"]
    export_mod["export.py\nYAML / CSV reproducible export"]

    schema --> engine
    entities --> engine
    events --> engine
    engine --> metrics
    interventions --> montecarlo
    metrics --> montecarlo
    montecarlo --> export_mod
  end

  subgraph optimize["shelterpulse/optimize"]
    interface["interface.py\nevaluate_candidate() · EvaluationResult\nCandidateAllocation"]
    baselines["baselines.py\nEqual · all-in · heuristic · random · grid"]
    jaxbo_opt["jaxbo_optimizer.py\njaxbo plugin"]
    workflow["workflow.py\nTemporal workflow stub\n(TEMPORAL_ENABLED = False)"]

    interface --> baselines
    interface --> jaxbo_opt
    interface --> workflow
  end

  subgraph adapters["Adapters  —  thin I/O wrappers"]
    api_app["api/app.py\nFastAPI: /scenario /simulate\n/compare /optimize /export"]
    cli_main["cli/main.py\nTyper commands"]
    ui_app["ui/\nNext.js + React + TypeScript\n+ Tailwind CSS"]
  end

  core --> optimize
  core --> api_app
  core --> cli_main
  api_app --> ui_app

  style core fill:#e8f4e8,stroke:#2d7a2d
  style optimize fill:#e8ecf4,stroke:#2d3d7a
  style adapters fill:#f4ece8,stroke:#7a3d2d
```

## The key invariant

```
shelterpulse.core  imports from  nowhere in shelterpulse.*
```

Enforced by `tests/unit/test_no_cross_imports.py` which runs in CI on every PR.
