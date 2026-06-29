# Playbook: PR Flows and CI/CD Implications

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
gh pr merge <pr-number> --squash --delete-branch
```

Always squash. Always delete the source branch.

### After merge

CI re-runs on develop HEAD. Orchestrator verifies green before promoting to main.

---

## develop → main (promotion)

### When to promote

- After completing a full phase (all gate criteria met)
- When develop is stable and CI is green
- Before tagging a release

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
  --title "chore: promote develop to main -- Phase <N> complete" \
  --body "Phase <N> gate passed. All CI green on develop."

gh pr merge <number> --squash
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
LIVE="https://sh-f52a79071fe149e0ac99448fc11e8496.ecs.us-east-1.on.aws"
curl "$LIVE/api/health"    # expect: {"status":"ok"}
curl -I "$LIVE/en"         # expect: HTTP/2 200
```

---

## CI Failure Triage

| Failure | Root cause | Fix |
|---------|-----------|-----|
| `test_no_cross_imports` | core/ imports from api/cli/optimize | Remove the bad import |
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
