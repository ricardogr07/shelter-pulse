# Worker: Deployment

**Model:** Claude Sonnet 4.6 | **Effort:** medium

**Role:** Build Docker images, push to ECR, trigger ECS rolling update, verify live URL.

## Architecture: ECS Express Mode

Single consolidated container: nginx (port 80) + uvicorn (internal 8000).
- nginx serves `/` and `/en/*` → Next.js static export (built into image)
- nginx proxies `/api/*` → uvicorn FastAPI
- One ALB, one HTTPS URL. Same origin = no CORS.

## ECR Repository

Name: `shelterpulse` (us-east-1)
URI: `<account>.dkr.ecr.us-east-1.amazonaws.com/shelterpulse`

Get account ID:
```bash
aws sts get-caller-identity --query Account --output text
```

## Manual Deploy

```bash
# 1. Authenticate to ECR
AWS_ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
aws ecr get-login-password --region us-east-1 | docker login \
  --username AWS \
  --password-stdin $AWS_ACCOUNT.dkr.ecr.us-east-1.amazonaws.com

# 2. Build the consolidated app target
docker build --target app -t shelterpulse:latest .

# 3. Tag + push
ECR_URI="$AWS_ACCOUNT.dkr.ecr.us-east-1.amazonaws.com/shelterpulse"
docker tag shelterpulse:latest $ECR_URI:latest
docker push $ECR_URI:latest

# 4. Force ECS to pull the new image
aws ecs update-service \
  --cluster shelterpulse \
  --service shelterpulse \
  --force-new-deployment \
  --region us-east-1
```

## Automated Deploy (normal path)

Tags are never created manually -- `git tag` + `git push` for a release tag is not allowed
(see `.github/workflows.md`). Instead:

- **Normal**: push a commit to `main` (via the develop → main PR flow). `auto-release.yml`
  reads conventional-commit prefixes since the last tag, bumps semver, creates the tag and
  GitHub Release, and calls `deploy.yml` directly. Skip a release for a given push with
  `[skip release]` or `[no release]` in the commit message.
- **Manual hotfix escape hatch**: trigger `release.yml` via `workflow_dispatch` (Actions tab)
  for a controlled/specific version outside the automatic flow.

Either way, `deploy.yml` runs: OIDC auth → build → ECR push → ECS update → post-deploy
smoke tests. Allow 3-5 minutes for the rolling update before verifying.

## Verify Live URL

```bash
LIVE="https://shelter-pulse.com"

# Health check
curl "$LIVE/api/health"
# Expect: {"status":"ok"}

# UI check
curl -I "$LIVE/en"
# Expect: HTTP/2 200

# Optimizer smoke test (quick, no-BO)
curl -s -X POST "$LIVE/api/optimize" \
  -H "Content-Type: application/json" \
  -d '{"n_candidates": 2, "n_reps": 4, "use_bo": false}' \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'Results: {len(d[\"results\"])} allocations')"

# Check for CORS errors -- open browser console at $LIVE/en and run the optimizer wizard
```

## NEVER

- Hard-code AWS credentials in any file
- Run `terraform destroy` (Terraform worker's domain, Director must approve)
- Push to ECR before running `tox -e test` locally
- Manually edit ECS task definitions or service config -- use Terraform or tags
