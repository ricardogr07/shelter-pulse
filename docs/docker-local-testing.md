# Docker Local Testing

All infrastructure changes must be verified locally before pushing or promoting to production.

## Quick Start

```bash
docker compose up --build -d
```

This starts 4 services:
- **api** (port 8000): FastAPI with QUEUE_BACKEND=rabbitmq
- **ui** (port 3000): Next.js static export via nginx
- **rabbitmq** (port 5672): Message broker for async jobs
- **worker**: Consumes optimization jobs from RabbitMQ

## Verify Health

```bash
curl http://localhost:8000/health
# {"status":"ok","scenario":"Whisker Haven"}

curl http://localhost:3000/en
# HTML response
```

## Test the Async Flow

```bash
# Submit an async optimization
curl -X POST http://localhost:8000/optimize/builder \
  -H 'Content-Type: application/json' \
  -d '{"duration_days":30,"housing_capacity":20,"n_replications":4}'
# Returns: {"job_id":"...","status":"queued"}

# Poll for completion
curl http://localhost:8000/optimize/<job_id>/status
# Returns: {"status":"completed",...}

# Get results
curl http://localhost:8000/optimize/<job_id>/results
# Returns: [{...}, ...]
```

## Running Tests

### Unit + E2E (no Docker needed)
```bash
uv run pytest tests/unit/ tests/e2e/ -v
```

### Integration (requires Docker running)
```bash
uv run pytest tests/integration/ -v
```

Integration tests verify the full async flow: API -> RabbitMQ -> Worker -> Webhook -> Results.

## Scaling Workers

```bash
docker compose up --scale worker=4 -d
```

Multiple workers consume from the same RabbitMQ queue concurrently.

## Checking Worker Logs

```bash
docker logs shelter-pulse-worker-1 --tail 20
```

## Promote to Production Flow

1. **Feature branch** -> local docker-compose test -> PR to develop -> CI green -> merge
2. **develop -> main**: PR with full e2e + promote workflow
3. **Deploy**: Tag-based (`v*` tag triggers deploy workflow)
4. **Smoke test**: Verify live URL responds (health + basic API calls)
5. **Rollback if needed**: Redeploy previous image tag via:
   ```bash
   aws ecs update-express-gateway-service \
     --service-arn $SERVICE_ARN \
     --primary-container "{\"image\":\"$ECR_REPO:v$PREV_VERSION\",\"containerPort\":8080}"
   ```

## Production vs Local Differences

| Aspect | Local (docker-compose) | Production (AWS) |
|--------|----------------------|------------------|
| Queue | RabbitMQ container | SQS FIFO queue |
| Worker | Docker container | Lambda function |
| Storage | Docker volume | EFS file system |
| Feature flag | QUEUE_BACKEND=rabbitmq | QUEUE_BACKEND=sqs |
| Progress | RabbitMQ progress queue | Webhook POST |

## Troubleshooting

### Worker not connecting to RabbitMQ
Check that rabbitmq container is healthy: `docker compose ps`
Worker retries connection 10 times with exponential backoff.

### API returning 500 on /optimize/builder
Check API logs: `docker logs shelter-pulse-api-1 --tail 30`
Common cause: aio-pika not installed (need `--extra worker` in Dockerfile).

### Stale images
```bash
docker compose down
docker compose up --build -d
```
