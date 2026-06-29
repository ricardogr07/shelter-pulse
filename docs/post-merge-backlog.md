# Post-Merge Backlog

> After all 7 PRs land on `develop`, pick up these items before promoting to `main`.

## Priority 1: Backend Implementation (blocks UI)

### 1.1 Optimizer Rewrite (`shelterpulse/optimize/jaxbo_optimizer.py`)

The current optimizer does random multi-start search. Needs a real GP+EI (Gaussian Process + Expected Improvement) loop with scipy fallback:
- Sequential acquisition: fit GP on evaluated points → maximize EI → evaluate → repeat
- Add `warm_start: list[EvaluationResult] | None = None` parameter
- Dirichlet sampling for initial random candidates
- The `test_gp_optimizer.py` tests define the expected interface

### 1.2 Baselines Fix (`shelterpulse/optimize/baselines.py`)

- Add `all_in_events` baseline (100% into adoption events)
- Fix `domain_heuristic`: remove clinic hours allocation (it made overflow *worse* in testing). Use foster + isolation + events only
- Update `ALL_BASELINES` dict to include 5 entries

### 1.3 Scenario Tuning (`scenarios/whisker_haven.yaml`)

Current scenario (housing=80, foster=40) never overflows — BO is meaningless. Needs:
- `housing_capacity: 35`
- `isolation_capacity: 5`
- `foster_network.capacity: 8`
- `intake_rate_per_day: 3.8`
- Kitten season `intake_multiplier: 2.5`
- These values produce ~234 overflow cat-days with zero intervention, 0 with all events

### 1.4 API Builder Endpoints (`shelterpulse/api/app.py`)

Add four new endpoints:
- `POST /simulate/custom` — accepts full scenario YAML-like body
- `POST /optimize/custom` — optimizes against custom scenario
- `POST /simulate/builder` — simplified params (the 9 fields from the UI form)
- `POST /optimize/builder` — optimize with simplified params
- Add `POST /sensitivity` — tornado chart data (vary each param ±20%, report overflow)
- Add `POST /timeline` — daily snapshot of housing_used + overflow for a simulation run

### 1.5 CLI Enhancements (`shelterpulse/cli/main.py`)

- `--scenario PATH` flag on simulate/optimize commands
- `--json` flag for machine-readable output
- `--quiet` flag to suppress progress output

### 1.6 Precomputed Cache

- Run `scripts/precompute_demo.py` after scenario tuning to generate `scenarios/whisker_haven_cache.pkl`
- Add cache-hit logic to `/optimize` endpoint (serve in <100ms when demo params match)

## Priority 2: UI Wiring

### 2.1 Root Page Redirect (`ui/src/app/page.tsx`)

Current root page has the old demo wizard. Needs to either:
- Redirect to `/en` (landing page), OR
- Become a simple server component that renders the landing page at `/`

### 2.2 API + Types Stubs → Real Implementation (`ui/src/api.ts`, `ui/src/types.ts`)

Replace the stub functions added for CI compliance with real implementations once backend endpoints exist:
- `simulateCustom()` → calls `/simulate/builder`
- `optimizeCustom()` → calls `/optimize/builder`
- `getSensitivity()` → calls `/sensitivity`
- `getTimeline()` → calls `/timeline`

### 2.3 Root Layout (`ui/src/app/layout.tsx`)

Consider whether the root layout should include NavBar for the `/` route or only under `[lang]/`.

## Priority 3: Docker Polish

### 3.1 Dockerfile Updates

- Add `COPY ui/nginx.conf /etc/nginx/conf.d/default.conf` to the UI target stage
- The `nginx.conf` handles locale-based URL routing (`/en/demo` → `en/demo.html`)

### 3.2 End-to-End Docker Verification

After backend + UI wiring complete:
```bash
docker compose down && docker compose up -d --build
# Verify: /en/demo, /es/demo, /en/simulate, API endpoints
```

## Priority 4: Test Fixes

### 4.1 Skip or Fix Failing Tests

Tests committed in PRs 2 and 7 may fail until backend work is done:
- `test_gp_optimizer.py` — needs optimizer rewrite (warm_start param)
- `test_cli.py` — needs CLI flag implementation
- `test_sensitivity.py` — needs `/sensitivity` endpoint
- `test_timeline.py` — needs `/timeline` endpoint
- `test_uncertainty.py` — needs confidence interval data

Add `@pytest.mark.skip(reason="pending backend implementation")` if committing before implementation, then remove skips after each piece lands.

## Out of Scope (deferred indefinitely)

- French / Portuguese translations (decided: en + es only)
- Step-by-step guided builder (multi-step wizard for custom scenarios)
- Offload optimization to k8s/Temporal/RabbitMQ workers
- GPU containers for JAX-BO
