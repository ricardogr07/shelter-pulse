# Worker: Deployment

**Model:** Claude Sonnet 4.6 | **Effort:** medium | **Phase:** 7

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

## Manual Deploy (Phase 7)

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

## Automated Deploy (CD via git tag)

```bash
git checkout main && git pull
git tag v<major>.<minor>.<patch>
git push origin v<major>.<minor>.<patch>
```

`deploy.yml` runs automatically: OIDC auth → build → ECR push → ECS update.
Allow 3-5 minutes for rolling update before verifying.

## Verify Live URL

```bash
LIVE="https://sh-f52a79071fe149e0ac99448fc11e8496.ecs.us-east-1.on.aws"

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

## Phase 7 Tasks

**Issue #33 (push image):** Run manual deploy steps above.
**Issue #34 (verify live):** Run all verification commands. Open browser at `$LIVE/en`,
run optimizer wizard end-to-end, confirm no CORS errors in browser console.

## NEVER

- Hard-code AWS credentials in any file
- Run `terraform destroy` (Terraform worker's domain, Director must approve)
- Push to ECR before running `uv run pytest tests/unit/ -v` locally
- Manually edit ECS task definitions or service config -- use Terraform or tags
