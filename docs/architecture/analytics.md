# Analytics Architecture (Phase 4)

Describes the new API endpoints, engine changes, and UI components for Pareto
frontier analysis, uncertainty visualization, sensitivity analysis, and time-series replay.

---

## 1. Pareto Frontier (`POST /pareto`)

### What it does
Sweeps the overflow-vs-cost tradeoff space by varying the optimization objective weight.
Returns a list of Pareto-optimal allocations: the efficient frontier.

### API contract

```python
class ParetoRequest(BaseModel):
    scenario_slug: str = "whisker-haven"
    n_points: int = 15          # number of points on the frontier
    n_replications: int = 32
    use_bo: bool = True

class ParetoPoint(BaseModel):
    allocation: AllocationOut
    mean_overflow_cat_days: float
    mean_total_cost: float
    ci_95_overflow: tuple[float, float]

# Response: list[ParetoPoint], sorted by mean_overflow_cat_days ascending
```

### Implementation note
Run `n_points` separate sweeps, each with a different scalarized objective:
`minimize: α * overflow + (1-α) * normalized_cost` for α ∈ [0, 1].
Requires Phase 5 (Temporal) for acceptable latency at n_points > 10.

---

## 2. Uncertainty Bands

No new endpoint needed: `MonteCarloSummary` already exposes `ci_95_lower` / `ci_95_upper`.
The change is in the UI: all overflow metrics display as `[mean] ± CI` with a shaded range bar.

```typescript
// ui/src/components/UncertaintyBar.tsx
interface UncertaintyBarProps {
  mean: number
  lower: number
  upper: number
  domain: number  // max value for scaling
}
```

---

## 3. Sensitivity Analysis (`POST /sensitivity`)

### What it does
Varies one scenario parameter by ±Δ% and re-runs the baseline simulation.
Returns a table of `(parameter, delta, mean_overflow, mean_cost)` rows.

### API contract

```python
class SensitivityRequest(BaseModel):
    scenario_slug: str = "whisker-haven"
    parameter: str          # e.g. "intake_rate_per_day", "isolation_fraction"
    deltas: list[float]     # e.g. [-0.2, -0.1, 0.0, 0.1, 0.2]
    n_replications: int = 32

class SensitivityRow(BaseModel):
    parameter: str
    delta: float            # fractional change, e.g. 0.2 = +20%
    mean_overflow_cat_days: float
    mean_total_cost: float
```

### Implementation
Mutate the frozen Scenario model by constructing a new one via `model_copy(update={...})`.
`core/` stays pure: the sensitivity sweep is implemented in `optimize/sensitivity.py` (new file).

---

## 4. Time-Series Replay (`GET /simulation/{run_id}/timeline`)

### Engine change required
`core/engine.py` must emit an optional event log when `record_timeline=True`.
This is a breaking change to the `run_simulation` signature:

```python
def run_simulation(
    scenario: Scenario,
    seed: int,
    intervention: InterventionParams | None = None,
    record_timeline: bool = False,      # new param: False by default
) -> SimulationResult:
    ...
```

When `record_timeline=True`, the engine appends a `TimeSnapshot` every simulated day:

```python
@dataclasses.dataclass(frozen=True)
class TimeSnapshot:
    day: int
    isolation_queue_depth: int
    housing_occupancy: int
    foster_active: int
    pending_adoption: int

@dataclasses.dataclass(frozen=True)
class SimulationResult:
    ...existing fields...
    timeline: list[TimeSnapshot] | None = None
```

### API contract

```
POST /simulate  { ..., record_timeline: true }
→ SimulationResponse { ..., timeline: list[TimeSnapshot] }
```

No separate route needed: it's a flag on the existing simulate endpoint.

---

## Chart library decision

Phase 1 used inline `<div style={{ width: X% }}>` for bars: works for simple comparisons.
Phase 4 needs: Pareto scatter plot, sensitivity tornado chart, time-series line chart.
These are not achievable with CSS-only bars.

**Decision:** Add `recharts` to `ui/package.json`.
- 45KB gzipped, tree-shakeable, composable React components
- Actively maintained, Next.js-compatible
- This is the one external chart dependency justified by the feature requirements

No other charting dependencies.
