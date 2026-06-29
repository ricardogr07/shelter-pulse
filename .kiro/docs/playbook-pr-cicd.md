# Playbook: PR Flows and CI/CD Implications

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

---

## Versioning Convention

**Scheme:** Semantic Versioning (`MAJOR.MINOR.PATCH`)

| Bump | When | Examples |
|------|------|----------|
| PATCH (0.1.1 → 0.1.2) | Bug fixes, security patches, infra changes, no new user-facing behavior | Security scan fixes, action pinning, nginx port change |
| MINOR (0.1.x → 0.2.0) | New features, new endpoints, new UI pages, breaking infra requiring config change | New optimizer, new page, new CLI command |
| MAJOR (0.x → 1.0.0) | Public API contract break, schema change that breaks existing clients | Post-hackathon production release |

**Decision rule:** When in doubt, it's a PATCH unless you added something a user would notice.

**How to tag:**

```bash
git checkout main && git pull
git tag v<MAJOR>.<MINOR>.<PATCH>
git push origin v<MAJOR>.<MINOR>.<PATCH>
```

Or use `release.yml` workflow dispatch (validates semver, creates GitHub Release, triggers deploy).


---

## Promotion Example: feat/issue-29-aikido-security-scan → v0.1.2

### Step 1: Push and PR to develop

```bash
git add -A
git commit -m "security: fix all Aikido scan findings

- Fix XSS: replace dangerouslySetInnerHTML with katex.render() DOM API
- Fix IaC: enable DynamoDB PITR, ECR encryption at rest
- Fix supply chain: pin all 3rd-party GH Actions to SHA
- Fix Docker: non-root user (appuser), nginx on port 8080
- Fix integrity: SHA256 verify AWS CLI download
- Fix credentials: persist-credentials: false on checkout
- Fix license: add Apache-2.0 LICENSE file
- Add smoke test script, Cypress specs, local dev playbook

Closes #26, closes #27, closes #28, closes #29"

git push -u origin feat/issue-29-aikido-security-scan

gh pr create --base develop \
  --title "security: fix all Aikido scan findings" \
  --body "Closes #26, #27, #28, #29. See commit message for full list."
```

### Step 2: Wait for CI (ci.yml)

CI validates:
- Python tests pass (pinned SHA actions still checkout correctly)
- UI builds (HowItWorksClient.tsx compiles without dangerouslySetInnerHTML)
- Docker `app` target builds (non-root user, nginx on 8080)

### Step 3: Merge to develop

```bash
gh pr merge --squash --delete-branch
```

### Step 4: PR develop → main

```bash
git checkout develop && git pull
gh pr create --base main --head develop \
  --title "chore: promote develop to main -- Phase 6 complete" \
  --body "Phase 6 gate: Aikido scan report committed, all findings fixed."
```

promote.yml runs: full tests + Docker build + GHCR push.

### Step 5: Merge to main

```bash
gh pr merge --squash
```

### Step 6: Tag and deploy

```bash
git checkout main && git pull
git tag v0.1.2
git push origin v0.1.2
```

deploy.yml: OIDC auth → ECR push → ECS update (containerPort: 8080).

### Step 7: Verify live

```bash
LIVE="https://sh-f52a79071fe149e0ac99448fc11e8496.ecs.us-east-1.on.aws"
curl "$LIVE/api/health"    # expect: {"status":"ok"}
curl -I "$LIVE/en"         # expect: HTTP/2 200
```

### Known risk: ECS containerPort change

The ECS Express service was created with containerPort 80. This deploy changes it to 8080.
The deploy.yml passes `containerPort: 8080` in the update command. If ECS rejects the
port change on update, we will need to recreate the Express service with the new port.
