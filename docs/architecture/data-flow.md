# Data Flow

End-to-end request flow for the primary user journey: configure, simulate, optimize.

## Optimization sweep (primary path)

```mermaid
sequenceDiagram
    participant U as UI / CLI
    participant API as FastAPI (api/app.py)
    participant W as workflow.py
    participant I as interface.py
    participant E as engine.py

    U->>API: POST /optimize {n_candidates, n_reps, use_bo}
    API->>W: run_optimization_sweep(scenario, budget, n_candidates, seed_set, use_bo)

    Note over W: seed_set fixed here -- same seeds used for every candidate (CRN)

    W->>I: evaluate_candidate(baseline_alloc, scenario, seed_set)  [x5 baselines]
    loop same seed_set every time
        I->>E: run_simulation(scenario, seed, intervention)
        E-->>I: SimulationResult
    end
    I-->>W: EvaluationResult (mean/std overflow, cost, 95% CI)

    W->>I: evaluate_candidate(bo_alloc, scenario, seed_set)  [xn_candidates]
    loop same seed_set every time
        I->>E: run_simulation(scenario, seed, intervention)
        E-->>I: SimulationResult
    end
    I-->>W: EvaluationResult

    W->>W: rank: feasible first (cost <= budget), then overflow ascending
    W-->>API: list[EvaluationResult]
    API-->>U: ranked JSON
```

## Single simulation (timeline / sensitivity)

```mermaid
sequenceDiagram
    participant U as UI
    participant API as FastAPI
    participant E as engine.py

    U->>API: POST /simulate/timeline {allocation, n_reps}
    API->>E: run_simulation(scenario, seed=scenario.seed, intervention)
    E-->>API: SimulationResult (daily housing_used + overflow_queue snapshots)
    API-->>U: list[TimelinePoint] (day, housing_used, overflow)
```

## Sensitivity analysis (tornado chart)

```mermaid
sequenceDiagram
    participant U as UI
    participant API as FastAPI
    participant I as interface.py

    U->>API: POST /sensitivity {allocation, n_reps}
    loop for each of 3 params x {high, low} = 6 perturbations
        API->>I: evaluate_candidate(allocation, perturbed_scenario, seed_set)
        I-->>API: EvaluationResult
    end
    API-->>U: list[SensitivityPoint] (param, direction, overflow_mean)
```

## Schema flow

```mermaid
graph LR
    yaml["scenarios/whisker_haven.yaml"] -->|yaml.safe_load| raw["dict"]
    raw -->|Scenario.model_validate| model["Scenario\n(frozen Pydantic model)"]
    model -->|resolve_intervention| ip["InterventionParams\n(resource deltas)"]
    ip -->|run_simulation| result["SimulationResult\n(one replication)"]
    result -->|run_paired| mc["MonteCarloSummary\n(mean/std/95% CI)"]
    mc -->|JSON serialization| resp["API response\n(Pydantic response model)"]
    resp -->|fetch| ui["React state\n(TypeScript types)"]
```
