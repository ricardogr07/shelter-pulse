# ADR-006: Use FastAPI as the REST Adapter

**Status:** Accepted | **Date:** 2026-06-26

## Context

The architecture requires a REST API surface exposing scenario load, simulate, compare,
optimize, and export (scope lock §2.1 item 14). The API must be thin: all logic lives in
the pure core library.

## Decision

Use FastAPI 0.115+ with Uvicorn as the ASGI server. FastAPI is chosen for:
- Automatic OpenAPI/Swagger docs at `/docs`: serves as API documentation for the
  Documentation judging category at near-zero cost.
- Native Pydantic v2 integration: request/response validation reuses the same models
  as the core schema loader.
- Async support for long-running simulation endpoints (background tasks or streaming).

## Consequences

- Auto-generated `/docs` and `/redoc` pages require no manual documentation effort.
- Pydantic validation errors surface as 422 responses automatically.
- FastAPI's dependency injection makes it easy to mock the core for unit tests of the API layer.
- Uvicorn is production-ready for the demo deployment tier (Render/Railway/Fly.io).
