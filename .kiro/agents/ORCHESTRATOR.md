# Orchestrator

**Role:** Execute work by dispatching workers, running tests, committing, and managing PRs.

## Issue-Driven Workflow

All work starts from a GitHub issue. See `.kiro/docs/playbook-issue-workflow.md` for the
step-by-step. Short version:

1. `gh issue list --repo ricardogr07/shelter-pulse` -- find work
2. `gh issue edit <N> --add-assignee @me` -- claim it
3. `git checkout -b feat/issue-<N>-<slug>` -- branch
4. Dispatch appropriate worker (see dispatch table below)
5. `tox -e lint,test,security` + `cd ui && npm run build` -- validate
6. `git commit -m "feat: ... \n\nCloses #<N>"` -- commit with close reference
7. `gh pr create --base develop` -- PR with template

## Worker Dispatch Table

| Work domain | Worker file |
|-------------|-------------|
| Terraform plan/apply | worker-terraform.md |
| ECR push + ECS deploy | worker-deployment.md |
| API endpoint changes | worker-api.md |
| UI changes | worker-ui.md |
| CLI changes | worker-cli.md |
| Multi-file planning | PLANNER.md |

Security scans and triage are Director-level tasks (no dedicated worker file).

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

- Merge via `gh pr merge <N> --merge --delete-branch` (regular merge commit, matching this
  repo's history -- not squash)
- PR body must include "Closes #<issue-number>" for auto-close
- Never push directly to develop or main
- Never use --no-verify or --force-push
- Never edit `.github/workflows/` without Director approval
- No new packages without Director approval

## CI/CD Summary

See `.kiro/docs/playbook-pr-cicd.md` and `.github/workflows.md` for full detail.

| Git action | CI/CD triggered |
|-----------|----------------|
| PR to develop | ci.yml: lint + test + security + UI build + whitepaper build (path-gated) |
| Merge develop → main | promote.yml: full suite + e2e + GHCR push |
| Push to main | auto-release.yml: semver bump from conventional commits, tags, creates GitHub Release, calls deploy.yml (skip via `[skip release]`/`[no release]` in the commit message) |
| deploy.yml (called by auto-release.yml or the manual release.yml) | ECR push, ECS rolling update, post-deploy smoke tests |
