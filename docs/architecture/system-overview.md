# System Overview

ShelterPulse system context: who uses it and how the major pieces connect.

![System overview: a Shelter Manager's browser talks to the Next.js UI, which calls the FastAPI adapter over HTTP /api/*. Inside the API, requests flow through the sweep orchestrator and evaluation interface into the pure core simulation engine. The API also dispatches to a queue module, which fans out to one of three mutually exclusive backends: sync (in-process, default/CI), rabbitmq (docker-compose), or sqs (production, consumed by Lambda).](../images/system-overview.svg)

## Deployment modes

| Mode | UI | API | Queue backend | Notes |
|---|---|---|---|---|
| **Local (docker compose)** | nginx :3000 | uvicorn :8000 | RabbitMQ | 4 containers: api, ui, rabbitmq, worker |
| **Production** | same origin as API | nginx :8080 proxies to uvicorn | SQS + Lambda | One consolidated ECS Fargate task behind one ALB, no CORS |
| **CI / tests** | not started | in-process | sync | No external dependencies |

Production and local intentionally differ in topology (consolidated single container vs. four separate containers) but run the exact same application code, gated by the `QUEUE_BACKEND` env var — see [async-workers.md](async-workers.md).

## Key URLs

- Live app: https://shelter-pulse.com/en
- API docs: https://shelter-pulse.com/api/docs
- RabbitMQ (local): http://localhost:15672 (shelter/pulse)

## See also

- [Module Boundaries](module-boundaries.md) — the `core` isolation invariant
- [Data Flow](data-flow.md) — sequence diagrams for the primary request paths
- [Async Workers](async-workers.md) — queue abstraction, job lifecycle, current AWS resources
- [Deployment](deployment.md) — CI/CD pipeline, Terraform modules, Dockerfile targets
