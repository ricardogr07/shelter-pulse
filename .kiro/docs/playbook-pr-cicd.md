# Playbook: PR Flows and CI/CD Implications

> **Partially retired (July 2026):** the release/deploy sections below describe the
> `auto-release.yml`/`deploy.yml`/`release.yml` pipeline that was removed in the static
> cutover (`docs/static-cutover.md`). Only `ci.yml` and `promote.yml` remain live; the
> PR-flow and local-gate guidance still applies.

## Pre-Push Local Gate

Run these before pushing. If you touched workflows, Docker, or nginx, steps 3-6 are mandatory.

### Always (every PR)

```bash
uv run pytest tests/unit/ -v                    # 1. Python tests
cd ui && npm run build                          # 2. UI build (TypeScript + static export)
```

### When Docker/nginx/workflows changed

```bash
# 3. Build consolidated image (simulates what CI + ECS will run)
docker build --target app -t shelterpulse:local --build-arg NEXT_PUBLIC_API_URL=/api .

# 4. Run it locally
docker run --rm -d -p 8080:8080 --name sp-gate shelterpulse:local

# 5. Smoke test against it
uv run python scripts/smoke_test.py

# 6. Cleanup
docker stop sp-gate
```

### When UI changed

```bash
cd ui && npx cypress run                        # 7. Cypress e2e against docker compose or static serve
```

### All green? Push and create PR.

If any step fails, fix locally before pushing. Do not rely on CI to catch what you can verify in 2 minutes.

---

## Branch Target Table

| Branch type | Target | CI workflow |
|-------------|--------|------------|
| `feat/*`, `fix/*`, `docs/*`, `chore/*` | `develop` | ci.yml |
| `develop` (via PR) | `main` | promote.yml |
| `v*` tag pushed on `main` | -- (deploy) | deploy.yml |

---

## feat/* → develop

### What ci.yml runs

1. **tox -e lint** -- pyrefly type check (fails on missing annotations, wrong types)
2. **tox -e test** -- full pytest suite including:
   - `test_conservation.py` (engine mass balance -- must never fail)
   - `test_no_cross_imports.py` (core purity -- must never fail)
   - All unit and e2e tests
3. **tox -e security** -- bandit scan (A-severity findings fail the build)
4. **cd ui && npm run build** -- TypeScript check + Next.js static export

All 4 checks must be green. Fix locally before pushing.

### Merge

```bash
gh pr merge <pr-number> --merge --delete-branch
```

Regular merge commit (matches this repo's history), not squash. Always delete the source branch.

### After merge

CI re-runs on develop HEAD. Orchestrator verifies green before promoting to main.

---

## develop → main (promotion)

### When to promote

- After a meaningful batch of work is merged to develop and gate criteria are met
  (see `.kiro/agents/DIRECTOR.md`)
- When develop is stable and CI is green
- Before a release

### What promote.yml runs

1. Full test suite (same as ci.yml)
2. `docker build --target app .` (validates Dockerfile + nginx-app.conf)
3. GHCR image push: `ghcr.io/ricardogr07/shelter-pulse:develop`

**promote.yml is stricter than ci.yml.** It validates the Docker build. If Docker fails,
fix before promoting (check Dockerfile targets, nginx-app.conf, static export output).

### Create the promotion PR

```bash
gh pr create \
  --base main \
  --head develop \
  --title "chore: promote develop to main" \
  --body "All CI green on develop."

gh pr merge <number> --merge
```

---

## v* tag → ECR + ECS deploy

### When to tag

After develop → main promotion, when ready to deploy to the live ECS service.

### Steps

```bash
git checkout main && git pull

# Semantic version: major.minor.patch
git tag v0.5.0
git push origin v0.5.0
```

### What deploy.yml runs

1. Authenticate to AWS via GitHub OIDC (`AWS_ROLE_ARN` secret -- no static credentials)
2. `docker build --target app -t shelterpulse:<tag> .`
3. Push to ECR: `<account>.dkr.ecr.us-east-1.amazonaws.com/shelterpulse:<tag>`
4. ECS rolling update: old tasks drain, new tasks start with new image

Allow 3-5 minutes. Then verify:

```bash
LIVE="https://shelter-pulse.com"
curl "$LIVE/api/health"    # expect: {"status":"ok"}
curl -I "$LIVE/en"         # expect: HTTP/2 200
```

---

## CI Failure Triage

| Failure | Root cause | Fix |
|---------|-----------|-----|
| `test_no_cross_imports` | core/ imports from api/ or cli/ | Remove the bad import |
| `test_conservation` | engine.py changed total cat count | Fix mass balance in engine |
| `tox -e lint` pyrefly | Missing or wrong type annotation | Add or fix annotation |
| `npm run build` | TypeScript error, missing export | Fix TS error or add stub |
| Docker build | COPY path wrong, missing file, nginx syntax | Check Dockerfile + nginx-app.conf |
| promote.yml Docker | Next.js build output missing | Verify `npm run build` locally first |

### Never bypass CI

```bash
# These are FORBIDDEN without explicit Director approval:
git commit --no-verify
gh pr merge --admin
```

---

## Versioning Convention

**Scheme:** Semantic Versioning (`MAJOR.MINOR.PATCH`)

| Bump | When | Examples |
|------|------|----------|
| PATCH (0.1.1 → 0.1.2) | Bug fixes, security patches, infra changes, no new user-facing behavior | Security scan fixes, action pinning, nginx port change |
| MINOR (0.1.x → 0.2.0) | New features, new endpoints, new UI pages, breaking infra requiring config change | New optimizer, new page, new CLI command |
| MAJOR (0.x → 1.0.0) | Public API contract break, schema change that breaks existing clients | A breaking change to a public API contract |

**Decision rule:** When in doubt, it's a PATCH unless you added something a user would notice.

**How releases actually happen:** tags are never created manually (`git tag` + `git push` for
a release tag is not allowed). `auto-release.yml` reads conventional-commit prefixes
(`feat:`/`fix:`/`BREAKING CHANGE:`) since the last tag and bumps semver automatically on every
push to `main`; skip a release for a given push with `[skip release]`/`[no release]` in the
commit message. `release.yml` (manual `workflow_dispatch`) is kept as a hotfix escape hatch
for cases outside the automatic flow. See `.github/workflows.md` for full detail.
