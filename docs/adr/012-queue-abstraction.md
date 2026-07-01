# ADR-12: Queue Abstraction - RabbitMQ Local, SQS+Lambda Production

**Status:** Accepted
**Date:** 2026-06-30
**Decision makers:** Ricardo (project lead)

## Context

The Bayesian Optimization sweep runs ~30s synchronously in the API process.
This blocks the HTTP connection and makes the API unresponsive during optimization.
We need to offload this to a background worker.

Options evaluated:
1. **Temporal** - Durable workflow engine with replay capability
2. **RabbitMQ everywhere** - Self-hosted message broker in ECS
3. **SQS+Lambda everywhere** - AWS-native serverless
4. **Hybrid: RabbitMQ local, SQS+Lambda prod** - Best of both worlds

## Decision

**Option 4: Hybrid with feature flag `QUEUE_BACKEND`**

- `QUEUE_BACKEND=sync` (default): In-process execution, no dependencies. Used for testing.
- `QUEUE_BACKEND=rabbitmq`: RabbitMQ broker + worker container. Used in docker-compose.
- `QUEUE_BACKEND=sqs`: SQS FIFO queue + Lambda consumer. Used in production.

A `QueuePublisher` protocol with three implementations ensures the API code doesn't
know or care which backend is active.

## Rationale

### Why not Temporal?
- Temporal Cloud: $100/month (blows entire budget)
- Self-hosted Temporal in ECS: ~512MB RAM minimum, complex setup
- Our workload is short-lived (~30s) and doesn't need durable replay
- Temporal adds value for long-running, multi-step workflows - not our case

### Why RabbitMQ locally?
- Demonstrates horizontal scaling: `docker compose up --scale worker=4`
- Judges see real message broker architecture knowledge
- Fast to develop against (no AWS credentials needed)
- Management UI at localhost:15672 for debugging

### Why SQS+Lambda in production?
- SQS: 1M requests/month free tier ($0 cost)
- Lambda: 1M invocations + 400K GB-seconds free tier ($0 cost)
- Lambda cold start ~1-3s acceptable (sweep takes 30s anyway)
- Lambda auto-scales with queue depth (no capacity planning)
- No infrastructure to manage or keep running 24/7

### Why not RabbitMQ in production?
- Always-on Fargate task: ~$10-15/month just for the broker
- Plus worker task: another ~$15/month
- Total ~$25/month for something that runs maybe 10 times/day
- SQS+Lambda costs $0 for that volume

## Consequences

- Three code paths to maintain (sync, rabbitmq, sqs)
- Lambda requires VPC + EFS for DuckDB access (adds ~1-3s cold start)
- Lambda container image must be lean (shelterpulse-core only, no FastAPI)
- Integration testing requires docker-compose (rabbitmq path) or localstack (sqs path)
- The sync fallback ensures all existing tests pass without any queue infrastructure

## Implementation

```
shelterpulse/queue/
  __init__.py           # Factory: get_publisher() reads QUEUE_BACKEND
  interface.py          # Protocol classes
  sync_backend.py       # In-process (default)
  rabbitmq_backend.py   # aio-pika publisher
  sqs_backend.py        # boto3 publisher
  rabbitmq_worker.py    # Consumer process for docker-compose
  job_store.py          # In-memory job state tracking

lambda/
  handler.py            # SQS event handler
  Dockerfile            # Lean container image
```
