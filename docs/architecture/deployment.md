# Deployment Architecture

Since the July 2026 static cutover, ShelterPulse has two deployment surfaces: a static public site and a local docker-compose stack. The ECS Express Mode service, ALB, and async worker fleet described in [ADR-007](../adr/007-ecs-express-mode.md), [ADR-008](../adr/008-queue-abstraction.md), and [ADR-010](../adr/010-async-worker-production-hardening.md) were torn down; see [static-cutover.md](../static-cutover.md) for the runbook and rollback path.

## Public site (production)

Static Next.js export (`NEXT_PUBLIC_STATIC_MODE=true`) on a private S3 bucket behind CloudFront:

- Bucket `shelterpulse-site-612962922955`, CloudFront distribution `E3QGGSZBB1R96B` with Origin Access Control and a URL-rewrite CloudFront Function for the flat export
- ACM certificate (`infra/dns`) covers apex + wildcard; Route 53 apex/www alias to CloudFront
- The demo replays a recorded Whisker Haven sweep; no backend, no compute, ~USD 0/month
- Deploy is `next build` + `aws s3 sync` + CloudFront invalidation (see [static-cutover.md](../static-cutover.md)); no CI deploy pipeline

## Local development (docker compose up)

```
docker compose up --build -d
```

Starts 2 services:
- **api** (port 8000): FastAPI + uvicorn; sweeps run synchronously in-process
- **ui** (port 3000): Next.js static export served by nginx, proxying `/api/*` to the api container

## Dockerfile targets

| Target | Purpose | Used by |
|--------|---------|--------|
| api | Python + uvicorn + optimize/store deps | docker-compose (api) |
| ui | nginx + Next.js static export | docker-compose (ui) |
| app | nginx + uvicorn consolidated (built on `api`) | GHCR image (promote workflow), local single-container runs |

## CI

- `ci.yml`: lint + tests + Docker build on every PR
- `promote.yml`: full checks + e2e + GHCR image push on PRs/pushes to `main`

The ECS release pipeline (`auto-release.yml`, `deploy.yml`, `release.yml`) was retired with the backend.

## Infrastructure (Terraform)

Terraform modules live in `infra/`, one state file per module (S3 backend, DynamoDB lock, `infra/backend.hcl`):

- **bootstrap**: S3 tfstate bucket + DynamoDB lock table (applied once, manually)
- **github-oidc**: GitHub Actions OIDC provider + role (kept; used by remaining AWS automation)
- **app-runner** (historical name): ECR repo `shelterpulse` + ECS-era IAM roles, kept for image rollback
- **dns**: ACM certificate + validation records, apex/www alias records to CloudFront

`infra/async-workers` (SQS, Lambda, EFS, NAT) was destroyed and deleted from the repo. The S3 bucket, CloudFront distribution, and CloudFront Function are currently hand-managed (codifying them as an `infra/static-site` module is the deferred Phase 4 of the retirement plan).
