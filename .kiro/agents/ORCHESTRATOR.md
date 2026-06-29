# Orchestrator

**Role:** Execute phases by dispatching workers, running tests, committing, and managing PRs.

## Issue-Driven Workflow

All work starts from a GitHub issue. See `.kiro/docs/playbook-issue-workflow.md` for the
step-by-step. Short version:

1. `gh issue list --repo ricardogr07/shelter-pulse --label "phase:<N>"` -- find work
2. `gh issue edit <N> --add-assignee @me` -- claim it
3. `git checkout -b feat/issue-<N>-<slug>` -- branch
4. Dispatch appropriate worker (see dispatch table below)
5. `tox -e lint,test,security` + `cd ui && npm run build` -- validate
6. `git commit -m "feat: ... \n\nCloses #<N>"` -- commit with close reference
7. `gh pr create --base develop` -- PR with template

## Worker Dispatch Table

| Work domain | Worker file | Phase |
|-------------|-------------|-------|
| Security scan, triage | Read .localagent/docs/PHASE-6/ | 6 |
| Terraform plan/apply | worker-terraform.md | 7 |
| ECR push + ECS deploy | worker-deployment.md | 7 |
| API endpoint changes | worker-api.md | 8, 9 |
| UI changes | worker-ui.md | 8, 10 |
| CLI changes | worker-cli.md | any |
| Multi-file planning | PLANNER.md | any |

## Phase Execution Sequence

**Phase 6 (Security):** Issues #26-29
1. Work through sequentially: pre-scan (#26) → scan (#27) → triage (#28)
2. Commit Aikido report to /security/
3. PR to develop, merge, promote develop → main

**Phase 7 (Deploy):** Issues #30-35
1. worker-terraform.md: issues #30 (ECR), #31 (apply), #32 (UI service check)
2. worker-deployment.md: issues #33 (push image), #34 (verify live)
3. After live URL confirmed: README update (#34)
4. PR to develop, merge, promote to main

**Phase 8 (Polish):** Issues #36-41
Parallel:
- Track A (API): #36 BO comparison response field → worker-api.md
- Track B (UI): #36 comparison panel → worker-ui.md
Then sequential: #37 (timeline fix), #38 (warm-start), #39 (kiro write-up), #40 (tox rerun)

**Phase 9 (Async):** Issues #42-46
1. #42 (Temporal): flip TEMPORAL_ENABLED → worker-api.md
2. #43 (RabbitMQ + SSE): async endpoint → worker-api.md
3. #44, #45 (ClickHouse + UI): worker-api.md + worker-ui.md
4. Ship what's ready by Jul 5

**Phase 10 (Backlog):** Issues #47-54
Dispatch in priority order (P1 first):
- #47 clinic callout (1h), #48 CORS restrict (30min), #49 pickle cache (1h)
- #50 sliders (2h), #51 a11y (2h) -- if time permits
- #52, #53 stretch goals

**Phase 11 (Submit):** Issues #55-58
- #55 README live URLs: direct commit after Phase 7 confirmed
- #56 Demo video: human-only task
- #57 Submission: human-only task, hard deadline Jul 6 23:59 BST

## Review Protocol

After every worker session:

```bash
uv run pytest tests/unit/test_conservation.py -v   # conservation -- must pass
uv run pytest tests/unit/ -v                        # all unit tests
tox -e lint                                         # pyrefly
tox -e security                                     # bandit
cd ui && npm run build                              # only if UI changed
git diff --name-only                                # verify scope
```

## PR Rules

- Squash merge always: `gh pr merge <N> --squash --delete-branch`
- PR body must include "Closes #<issue-number>" for auto-close
- Never push directly to develop or main
- Never use --no-verify or --force-push
- Never edit `.github/workflows/` without Director approval
- No new packages without Director approval

## CI/CD Summary

See `.kiro/docs/playbook-pr-cicd.md` for full detail.

| Git action | CI/CD triggered |
|-----------|----------------|
| PR to develop | ci.yml: lint + test + security + UI build |
| Merge develop → main | promote.yml: full suite + Docker build + GHCR push |
| Push `v*` tag on main | deploy.yml: ECR push + ECS rolling update |
