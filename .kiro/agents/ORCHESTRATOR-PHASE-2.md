# Orchestrator: Phase 2: UI Expansion

**Role:** Drive Phase 2 tracks to completion. Implement, review, test, and commit.

---

## Read first

1. @.kiro/agents/SHARED.md
2. @.localagent/docs/PHASE-2/00-index.md
3. @.localagent/docs/PHASE-2/STATUS.md

---

## Current state

Phase 1 complete. Running locally:
- `docker compose up` → UI localhost:3000, API localhost:8000
- 33/33 Python tests pass
- Single-page wizard at `/` (will move to `/demo`)
- No routing, no landing page, no custom sim

---

## Wave 2a: parallel, no external deps

### Track: 01-routing
Spec: @.localagent/docs/PHASE-2/01-routing.md

Implementation:
1. Create `ui/src/components/NavBar.tsx`: sticky nav with links to /, /demo, /simulate
2. Create `ui/src/components/Footer.tsx`: minimal footer
3. Update `ui/src/app/layout.tsx`: wrap children with NavBar + Footer
4. Create `ui/src/app/demo/page.tsx`: copy current `page.tsx` content here
5. Replace `ui/src/app/page.tsx`: placeholder "Landing page coming..."
6. Create `ui/src/app/simulate/page.tsx`: placeholder "Custom sim coming..."

Verify: `cd ui && npm run build` passes, `/demo` shows the wizard.

### Track: 04-custom-scenario-api
Spec: @.localagent/docs/PHASE-2/04-custom-scenario-api.md

Implementation:
1. Create `shelterpulse/api/custom.py`: `build_scenario_from_request()`
2. Add `POST /simulate/custom` and `POST /optimize/custom` to `api/app.py`
3. Create `tests/unit/test_custom_api.py`

Verify: `uv run pytest tests/unit/test_custom_api.py -v` passes, conservation test passes.

---

## Wave 2b: after Wave 2a done

### Track: 02-landing-page
Spec: @.localagent/docs/PHASE-2/02-landing-page.md

Implementation: Replace placeholder `page.tsx` with full landing page design (hero, problem, how-it-works, features, CTA).

### Track: 03-custom-simulation
Spec: @.localagent/docs/PHASE-2/03-custom-simulation.md

Implementation: Replace placeholder `simulate/page.tsx` with full form + results panel.
Add `simulateCustom` and `optimizeCustom` to `ui/src/api.ts`.

---

## After each track

```bash
uv run pytest tests/unit/ -q        # Python tests
cd ui && npm run build               # UI build
```

Update STATUS.md row → DONE.

---

## Phase gate

- [ ] `npm run build` clean with 3 routes (/, /demo, /simulate)
- [ ] Landing page at `/` with CTAs
- [ ] Custom sim at `/simulate`: form submits to API, results render
- [ ] Demo wizard at `/demo`: unchanged behavior
- [ ] All Python tests pass
