# System Overview

ShelterPulse system context: who uses it and how the major pieces connect.

Since the July 2026 static cutover, the public site is a **static Next.js export** on S3 + CloudFront that replays a recorded Whisker Haven sweep. The full application (UI + FastAPI + simulation core) runs locally via docker compose; every endpoint is synchronous and in-process. The queue/worker fan-out shown in older diagrams was retired (see [ADR-008](../adr/008-queue-abstraction.md) for the original design and [static-cutover.md](../static-cutover.md) for the retirement).

## Deployment modes

| Mode | UI | API | Notes |
|---|---|---|---|
| **Public site** | S3 + CloudFront static export | none | Recorded sweep, `NEXT_PUBLIC_STATIC_MODE=true`; ~USD 0/month |
| **Local (docker compose)** | nginx :3000 | uvicorn :8000 | 2 containers: api, ui; sweeps run in-process |
| **CI / tests** | not started | in-process | No external dependencies |

## Key URLs

- Live site: https://shelter-pulse.com/en

## See also

- [Module Boundaries](module-boundaries.md): the `core` isolation invariant
- [Data Flow](data-flow.md): sequence diagrams for the primary request paths
- [Deployment](deployment.md): static hosting, local compose, remaining Terraform
