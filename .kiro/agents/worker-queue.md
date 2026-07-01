---
inclusion: manual
---

# Worker Agent: Queue & Async Infrastructure

Specialist agent for the async worker infrastructure: queue abstraction, RabbitMQ, SQS, Lambda, job lifecycle.

## Ownership

This agent owns:
- `shelterpulse/queue/` (all files)
- `lambda/` (handler + Dockerfile)
- `docker/rabbitmq.Dockerfile`
- `docker-compose.yml` (rabbitmq + worker services)
- `tests/unit/test_queue_interface.py`
- `tests/unit/test_async_api.py`
- `tests/unit/test_lambda_sqs.py`
- `tests/integration/test_async_flow.py`

## Context

### Architecture
- Feature flag `QUEUE_BACKEND` (sync|rabbitmq|sqs) selects dispatch backend
- Sync: in-process, no deps (default for tests and CI)
- RabbitMQ: docker-compose local development
- SQS: production (Lambda consumer)

### Job Lifecycle
1. API creates job in job_store (queued)
2. Publisher dispatches to queue
3. Worker consumes, runs BO sweep
4. Worker calls webhook /internal/jobs/{id}/complete
5. job_store updated to completed with results

### Key Files
- `shelterpulse/queue/__init__.py` - Factory (get_publisher, get_progress_listener)
- `shelterpulse/queue/interface.py` - Protocol definitions
- `shelterpulse/queue/job_store.py` - In-memory state (JobStatus enum, Job dataclass, JobStore)
- `shelterpulse/queue/rabbitmq_worker.py` - Standalone consumer with retry logic
- `lambda/handler.py` - SQS event handler for AWS Lambda

### Environment Variables
| Var | Local | Prod |
|-----|-------|------|
| QUEUE_BACKEND | rabbitmq | sqs |
| RABBITMQ_URL | amqp://shelter:pulse@rabbitmq:5672/ | not set |
| SQS_QUEUE_URL | not set | https://sqs.us-east-1.amazonaws.com/... |
| API_URL | http://api:8000 | ALB URL |
| INTERNAL_KEY | dev-key-123 | random 32-char secret |

### Testing Requirements
- Unit tests must pass with QUEUE_BACKEND=sync (no infra needed)
- Integration tests require docker-compose up
- Always verify both sync and async paths before PR

### Rules
1. Never break the sync fallback - it's what CI uses
2. Worker must use only stdlib for HTTP (urllib.request) - no httpx in prod image
3. RabbitMQ worker must have retry logic (exponential backoff, 10 attempts)
4. Internal webhooks must validate X-Internal-Key header
5. Job store is in-memory for now - will be DuckDB in #44
6. Lambda handler must be stateless (no global mutable state)
