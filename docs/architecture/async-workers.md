# Async Workers Architecture

The BO optimization sweep (~30s) is offloaded to background workers via a queue abstraction.

## Architecture Diagram

### Production (AWS)
```
ECS Express Mode                              Lambda (VPC, EFS mount)
+-----------------------+                     +--------------------+
|  shelter-pulse:app    |--SQS publish------->|  shelterpulse-core |
|  (nginx + uvicorn)    |                     |  (BO worker)       |
|                       |<--webhook POST------|                    |
|  EFS: DuckDB (read)   |  /internal/progress |  EFS: DuckDB (w)   |
|  SSE -> UI            |                     +--------------------+
+-----------------------+
```

### Local (docker-compose)
```
API container          RabbitMQ              Worker container
+-------------+       +--------+            +-------------------+
|  uvicorn    |--pub-->| broker |<--cons-----|  shelterpulse-core|
|             |        |        |            |  (BO worker)      |
|             |<-------|progress|------------|                   |
|  DuckDB (r) |        +--------+            |  DuckDB (write)   |
|  SSE -> UI  |                              +-------------------+
+-------------+
```

## Feature Flag

`QUEUE_BACKEND` environment variable selects the dispatch backend:
- `sync` (default): In-process execution, no external dependencies. Tests use this.
- `rabbitmq`: Publishes to RabbitMQ. Worker containers consume. Used in docker-compose.
- `sqs`: Publishes to AWS SQS FIFO queue. Lambda consumes. Used in production.

## Job Lifecycle

```
1. UI calls POST /optimize/builder
2. API generates job_id, publishes to queue, returns 202 {job_id}
3. Worker consumes job, runs run_optimization_sweep()
4. Worker calls POST /internal/jobs/{job_id}/complete with results
5. UI polls GET /optimize/{job_id}/status until completed
6. UI fetches GET /optimize/{job_id}/results
```

## Queue Module Structure

```
shelterpulse/queue/
  __init__.py           # Factory: get_publisher() reads QUEUE_BACKEND
  interface.py          # Protocol: QueuePublisher, ProgressListener
  sync_backend.py       # In-process (no queue, default)
  rabbitmq_backend.py   # aio-pika publisher
  sqs_backend.py        # boto3 SQS publisher
  rabbitmq_worker.py    # Consumer process (docker-compose)
  job_store.py          # In-memory job state tracking
```

## Internal Webhook Endpoints

All authenticated via `X-Internal-Key` header:
- `POST /internal/jobs/{job_id}/progress` - Worker reports progress
- `POST /internal/jobs/{job_id}/complete` - Worker reports completion with results
- `POST /internal/jobs/{job_id}/fail` - Worker reports failure

## Lambda Worker

```
lambda/
  handler.py    # SQS event -> run_optimization -> webhook results
  Dockerfile    # python:3.12-slim + optimize deps + awslambdaric (lean)
```

Lambda is triggered by SQS event source mapping. Runs in VPC with EFS mount for DuckDB access. Cold start ~1-3s, sweep ~30s, within Lambda 15-min timeout.

## Cost

- SQS: 1M requests/month free tier ($0)
- Lambda: 1M invocations + 400K GB-seconds free tier ($0)
- RabbitMQ: only in docker-compose (no prod cost)
- Total additional AWS cost: $0

## See Also

- [ADR-12: Queue Abstraction](../adr/012-queue-abstraction.md)
- [Docker Local Testing](../docker-local-testing.md)
