# Data Flow

End-to-end request flow for the primary user journey: configure, simulate, optimize.

## Optimization sweep (primary path)

![Optimization sweep sequence diagram: UI/CLI posts to FastAPI, which calls workflow.py's run_optimization_sweep() with a fixed seed_set (CRN). Workflow.py loops interface.py's evaluate_candidate() over 5 baseline allocations, then over n_candidates BO-proposed allocations, each looping engine.py's run_simulation() with the same seed_set every time. Workflow.py ranks results (feasible first, then overflow ascending) and returns a ranked JSON list up through FastAPI to the UI/CLI.](../images/data-flow-optimization.svg)

## Single simulation (timeline) and sensitivity analysis (tornado chart)

![Two request flows side by side: left, "Single Simulation / Timeline" - UI posts to FastAPI, which calls engine.py's run_simulation() and returns a list of TimelinePoints. Right, "Sensitivity Analysis" - UI posts to FastAPI, which loops interface.py's evaluate_candidate() over 6 perturbations (3 params x high/low) and returns a list of SensitivityPoints.](../images/data-flow-simulation-sensitivity.svg)

## Schema flow

![Schema flow pipeline: scenarios/whisker_haven.yaml is parsed via yaml.safe_load into a raw dict, validated via Scenario.model_validate into a frozen Pydantic Scenario model, converted via resolve_intervention into InterventionParams, run through run_simulation into a SimulationResult, aggregated via run_paired into a MonteCarloSummary, JSON-serialized into the API response model, and fetched into React/TypeScript state on the frontend.](../images/schema-flow.svg)
