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

Flow: UI -> API -> RabbitMQ -> Worker -> API webhook -> UI polls results

## Production (AWS ECS Express Mode)

Single consolidated container (nginx + uvicorn) deployed via ECS Express Mode:
- nginx serves static Next.js export at /
- nginx proxies /api/* to uvicorn at :8000
- One ALB, one HTTPS URL, no CORS

Async workers in production:
- API publishes to SQS FIFO queue
- Lambda function consumes from SQS
- Lambda runs in VPC with EFS mount (for DuckDB)
- Lambda calls webhook on API with results

## Deploy pipeline

1. Push to develop: CI runs (lint + tests + Docker build)
2. PR develop -> main: promote workflow (full e2e + GHCR push)
3. Tag v*: release workflow triggers deploy workflow
4. Deploy: Build image, push to ECR, update ECS Express service
5. Rollback: Redeploy previous image tag

## Dockerfile targets

| Target | Purpose | Used by |
|--------|---------|--------|
| api | Python + uvicorn + optimize deps | docker-compose (api + worker) |
| ui | nginx + Next.js static export | docker-compose (ui) |
| app | nginx + uvicorn consolidated | ECS production |

## Infrastructure (no Terraform)

AWS resources are managed via CLI/console (hackathon scope).
See docs/aws-async-infra.md for production resources needed.
Future: IaC with CDK or Terraform when the project matures beyond hackathon.
