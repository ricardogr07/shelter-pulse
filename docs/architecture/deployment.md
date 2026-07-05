# Deployment Architecture

## Local development (docker compose up)

```
docker compose up --build -d
```

Starts 4 services:
- **rabbitmq** (port 5672): Message broker for async optimization jobs
- **api** (port 8000): FastAPI with QUEUE_BACKEND=rabbitmq, publishes to RabbitMQ
- **worker**: Consumes jobs from RabbitMQ, runs BO sweep, calls API webhook
- **ui** (port 3000): Next.js static export served by nginx

Flow: UI -> API -> RabbitMQ -> Worker -> API webhook -> UI polls/streams results

## Production (AWS ECS Express Mode)

Single consolidated container (nginx + uvicorn) deployed via ECS Express Mode, one Fargate task behind one ALB:
- nginx listens on :8080 (container port), serves the static Next.js export at `/`
- nginx proxies `/api/*` to uvicorn on `127.0.0.1:8000` (trailing slash strips the prefix)
- One ALB, one HTTPS URL, no CORS
- ALB has an HTTP (:80) listener that 301-redirects to HTTPS (:443); nginx's own root redirect (`/` → `/en`) follows `X-Forwarded-Proto` from the ALB when present, falling back to the request's own scheme for local `docker run -p 8080:8080` access

Async workers in production:
- API publishes to SQS FIFO queue (`shelterpulse-jobs.fifo`) via boto3
- Lambda function (`shelterpulse-worker`) consumes from SQS
- Lambda runs in VPC with EFS mount (for DuckDB persistence)
- Lambda calls a webhook back on the API with results, authenticated via `X-Internal-Key`

See [async-workers.md](async-workers.md) for the full diagram, current resource list, and the NAT Gateway that gives Lambda's VPC-attached ENIs a path to the internet for the webhook callback (see [ADR-010](../adr/010-async-worker-production-hardening.md)).

## Deploy pipeline

![Deploy pipeline: a feature branch merges to develop via PR + CI, develop merges to main via the promote workflow (full e2e + GHCR push), a push to main triggers the auto-release workflow which bumps semver from conventional commits and creates the tag + GitHub Release, which calls the deploy workflow to push images to ECR, roll out the ECS Express Mode service and conditionally update the Lambda function, then runs a post-deploy smoke test.](../images/deployment-pipeline.svg)

1. Push to `develop`: CI runs (lint + tests + Docker build)
2. PR `develop` -> `main`: promote workflow (full e2e + GHCR push)
3. Push to `main`: `auto-release.yml` reads conventional-commit prefixes since the last tag, bumps semver, creates the tag + GitHub Release, and calls `deploy.yml` directly (skippable per-push via `[skip release]`/`[no release]`). `release.yml` (manual `workflow_dispatch`) is a hotfix escape hatch for cases outside this automatic flow. Tags are never pushed manually.
4. Deploy: build image, push to ECR, `aws ecs update-express-gateway-service` (rolling deploy, zero-downtime), conditionally `aws lambda update-function-code` if `lambda/` changed since the previous tag
5. Smoke test: `scripts/smoke_test.py --quick` against the live URL
6. Rollback: redeploy previous image tag via the same `update-express-gateway-service` command

## Dockerfile targets

| Target | Purpose | Used by |
|--------|---------|--------|
| api | Python + uvicorn + optimize/worker/store/**aws** deps | docker-compose (api + worker) |
| ui | nginx + Next.js static export | docker-compose (ui) |
| app | nginx + uvicorn consolidated (built on `api`) | ECS production |

The `api`/`app` stages install the `aws` extra (`boto3`) — without it, any request that hits `QUEUE_BACKEND=sqs` fails with `ModuleNotFoundError` before it can publish to the queue. See [ADR-010](../adr/010-async-worker-production-hardening.md).

## Infrastructure (Terraform + some imperative CLI)

Terraform modules live in `infra/`, one state file per module (S3 backend, DynamoDB lock, `infra/backend.hcl`):

![Terraform module dependency graph: infra/bootstrap (S3 tfstate bucket + DynamoDB lock table, applied once manually) is the state backend for four dependent modules - infra/github-oidc (GitHub Actions OIDC provider + deploy role), infra/app-runner (historical name; ECR repo + ECS execution/task IAM roles), infra/async-workers (SQS + DLQ, Lambda + role, EFS, ECS task IAM role), and infra/dns (ACM cert, Route53 records, ALB HTTPS listener, redirects).](../images/terraform-modules.svg)

**Not Terraform-managed:** the ECS Express Mode service/task definition itself (`shelterpulse` service in the `default` cluster). AWS's ECS Express Mode Terraform resource requires AWS provider v6.x; this repo is pinned to v5.x (see [ADR-007](../adr/007-ecs-express-mode.md)). It's created/updated imperatively via `aws ecs update-express-gateway-service` (see `deploy.yml` and the deploy pipeline above). This means task-level settings not covered by that CLI call (like the task IAM role) are set with a one-off `--task-role-arn` flag rather than tracked in `main.tf`, even though the role itself *is* defined in Terraform (`infra/async-workers/main.tf`).

The ALB Express Mode creates (`ecs-express-gateway-alb-*`) is also not Terraform-managed, and its `idle_timeout.timeout_seconds` was manually raised from AWS's 60s default to **300s** (matching nginx's own `proxy_read_timeout`) via `aws elbv2 modify-load-balancer-attributes`, since several endpoints (`/sensitivity`, `/optimize/builder/compare`, the demo's synchronous `/optimize`, and the async worker's own webhook callback) can legitimately take longer than 60s to respond. If the ALB is ever recreated by Express Mode, this setting will reset to the 60s default and needs to be reapplied:

```
aws elbv2 modify-load-balancer-attributes \
  --load-balancer-arn <express-mode-alb-arn> \
  --attributes Key=idle_timeout.timeout_seconds,Value=300
```
