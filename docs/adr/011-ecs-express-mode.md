# ADR-011: Switch Cloud Deployment from App Runner to ECS Express Mode (Single Consolidated Service)

**Status:** Accepted (supersedes [ADR-008](008-aws-app-runner.md)) | **Date:** 2026-06-28

## Context

ADR-008 chose AWS App Runner. While wiring up the deployment we hit a hard wall:

- `apprunner CreateService` returns `SubscriptionRequiredException: The AWS Access Key Id
  needs a subscription for the service` on our account (612962922955).
- This is not an account-activation delay. Per AWS docs, **App Runner is no longer open to
  new customers as of April 30, 2026** — existing customers keep it, new accounts can never
  subscribe. Our account is new, so App Runner is permanently unavailable.

We want to stay on AWS (single-cloud lock-in is a deliberate goal). AWS's officially
recommended replacement for simple managed container deployments is **Amazon ECS Express
Mode** (GA at re:Invent 2025).

## Decision

Deploy ShelterPulse to **Amazon ECS Express Mode** as a **single consolidated container**.

Express Mode takes one container image plus two IAM roles and auto-provisions an
internet-facing ALB, Fargate tasks, auto-scaling, CloudWatch logging, canary deploys, and
a public HTTPS URL (`https://<service>.ecs.<region>.on.aws`) with automatic TLS — the same
"push image → get URL" simplicity App Runner offered.

**Single consolidated service (not two).** Instead of separate API and UI services (two
ALBs, two URLs, CORS, and a build-time `NEXT_PUBLIC_API_URL` coupling), one image runs:

- `uvicorn` (FastAPI) on `127.0.0.1:8000`
- `nginx` on `:80` serving the Next.js static export **and** reverse-proxying `/api/*`
  to uvicorn (stripping the `/api` prefix)

The UI is built with `NEXT_PUBLIC_API_URL=/api`, so the browser calls a same-origin
relative path. No CORS, one ALB, one URL, half the cost.

| Item | Choice |
|------|--------|
| Compute | ECS Express Mode (Fargate), 0.25 vCPU / 0.5 GB, min 1 task |
| Image | Single `app` Dockerfile target (python + nginx) in ECR repo `shelterpulse` |
| Health check | `/api/health` (proxied to uvicorn — also guards uvicorn liveness) |
| IaC | Terraform for ECR + the two IAM roles (provider v5); service created/updated via AWS CLI |
| CD | `deploy.yml` builds/pushes the consolidated image to ECR, then `aws ecs update-express-gateway-service` |

### Why CLI (not Terraform) for the service itself

Express Mode's Terraform resource requires AWS provider **v6.x**; this repo is pinned to
`~> 5.0`. A v5→v6 major bump is breaking and out of scope under the hackathon deadline.
AWS's own "GitHub Actions for ECS Express Mode" guide uses the CLI, so Terraform owns the
stable, v5-supported pieces (ECR repo, IAM roles) and the CLI owns the Express service.

## Consequences

- **Not free-tier-free.** Express Mode has no service charge, but the ALB (~$16/mo), Fargate
  compute (~$9/mo at 0.25 vCPU/0.5 GB), and public IPv4 (~$3.6/mo) are billable. $200 AWS
  credits cover the demo window comfortably. Tear the service down after judging to stop
  charges.
- Requires a **default VPC with public subnets** in us-east-1 (Express Mode default).
- One image is slightly more complex to build (two processes), but removes CORS, the
  build-time API-URL coupling, and the second ALB.
- `uvicorn` crash → `/api/health` fails → ECS replaces the task (liveness for free).
- ADR-007 (Render) and ADR-008 (App Runner) are both now superseded.

## ponytail note

Single process-supervisor is a 3-line shell script (`uvicorn &` then `nginx -g 'daemon
off;'`), not supervisord. Ceiling: if nginx exits the container exits; uvicorn liveness is
covered by the ALB health check. Upgrade path if needed: add a real init (tini/supervisord).
