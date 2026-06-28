# Orchestrator Protocol

**Role:** Execute phases by dispatching work (to subagents or directly), reviewing results,
running tests, and committing. This is the Kiro session acting as orchestrator.

---

## Read first

1. @.kiro/agents/SHARED.md
2. The relevant phase's `00-index.md` and `STATUS.md`
3. All spec files for the current phase's active wave

---

## Execution loop

```
1. Read STATUS.md for the current phase
2. Find tracks: Status=TODO AND all dependency tracks are DONE
3. For parallel tracks in the same wave → dispatch as subagents or do sequentially
4. After each track: run tests, verify done criteria
5. If pass: update STATUS.md → DONE
6. If fail: diagnose, fix, re-verify
7. When all tracks DONE → evaluate phase gate → move to next phase
```

---

## Phase 2 — UI Expansion (Jun 27–30)

### Wave 2a (parallel, no deps)
- **01-routing**: Move wizard to /demo, add NavBar + layout + /simulate placeholder
- **04-custom-scenario-api**: New `POST /simulate/custom` + `/optimize/custom` endpoints

### Wave 2b (after 2a)
- **02-landing-page**: Marketing-quality landing at `/`
- **03-custom-simulation**: Full form + results at `/simulate`

### Verify:
```bash
uv run pytest tests/unit/ -q              # all Python tests pass
cd ui && npm run build                     # Next.js builds clean
```

---

## Phase 3 — Analytics (Jul 1–3)

### Wave 3a (parallel)
- **01-sensitivity-api**: POST /sensitivity endpoint
- **02-time-series**: Engine event recorder + timeline endpoint
- **03-uncertainty-bands**: CI-95 fields in result models

### Wave 3b
- **04-analytics-ui**: Render sensitivity, timeline, CI on /simulate page

### Verify:
```bash
uv run pytest tests/unit/ -v              # includes new test files
uv run pytest tests/unit/test_conservation.py -v  # regression guard
cd ui && npm run build
```

---

## Phase 4 — Polish (Jul 3–5)

### Wave 4a (parallel, no deps)
- **01-security-scan**: pip-audit + npm audit → security/
- **04-temporal-gate**: Run gate test, document decision
- **.kiro/ commit**: git add .kiro/

### Wave 4b (after Phases 2+3)
- **02-demo-script**: Write docs/demo-script.md
- **03-ux-polish**: Loading, errors, responsive, a11y

### Verify:
```bash
uv run pytest -q
cd ui && npm run build
```

---

## Phase 5 — Cloud + Submission (Jul 5–7)

### Wave 5a
- **01-aws-setup**: User creates AWS Free Plan account

### Wave 5b (sequential)
- **02-cloud-deploy**: ECR + App Runner
- **03-readme-urls**: Update README with live URLs
- **04-demo-video**: Record < 5 min walkthrough
- **05-submission-checklist**: Final gate

### Verify:
```bash
curl <LIVE_API_URL>/health
# Open <LIVE_UI_URL> in browser, run full flow
```

---

## Review protocol (after each track)

```bash
# 1. Run relevant tests
uv run pytest tests/unit/ -q

# 2. Conservation guard (if core/ was touched)
uv run pytest tests/unit/test_conservation.py -v

# 3. Cross-import guard (if core/ was touched)
uv run pytest tests/unit/test_no_cross_imports.py -v

# 4. UI build (if ui/ was touched)
cd ui && npm run build
```

---

## Commit convention

```
feat: <track name> — <one-line description>
fix: <what was wrong>
docs: <documentation change>
chore: <non-functional change>
```

---

## Rules

- No `git push --force`, no `--amend`, no `--no-verify`
- No changes to `.github/workflows/`
- No new packages without Director approval
- Architecture questions → escalate to Director
