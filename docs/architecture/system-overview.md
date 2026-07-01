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

- Live app: https://sh-f52a79071fe149e0ac99448fc11e8496.ecs.us-east-1.on.aws/en
- API docs: https://sh-f52a79071fe149e0ac99448fc11e8496.ecs.us-east-1.on.aws/api/docs
- RabbitMQ (local): http://localhost:15672 (shelter/pulse)
