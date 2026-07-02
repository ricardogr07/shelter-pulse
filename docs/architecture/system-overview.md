# System Overview

ShelterPulse system context: who uses it and how the major pieces connect.

```
Shelter Manager (browser)
    |
    v
Next.js UI (static export, port 3000)
    |
    v [HTTP /api/*]
FastAPI (port 8000)
    |
    +---> optimize/workflow.py (sweep orchestrator)
    |         |
    |         v
    |     optimize/interface.py (evaluate_candidate)
    |         |
    |         v
    |     core/ (SimPy engine, schema, interventions, montecarlo)
    |
    +---> queue/ (async dispatch)
              |
              v [QUEUE_BACKEND flag]
         sync (in-process) | rabbitmq (docker) | sqs (prod/Lambda)
```

## Deployment modes

- **Local**: docker compose (API + UI + RabbitMQ + Worker)
- **Production**: ECS Express Mode (consolidated container) + SQS + Lambda
- **CI**: In-process (QUEUE_BACKEND=sync), no external dependencies

## Key URLs

- Live app: https://shelter-pulse.com/en
- API docs: https://shelter-pulse.com/api/docs
- RabbitMQ (local): http://localhost:15672 (shelter/pulse)
