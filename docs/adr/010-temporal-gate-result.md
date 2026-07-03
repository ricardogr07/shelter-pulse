> **SUPERSEDED by [ADR-012](012-queue-abstraction.md).** Current async execution uses SQS/Lambda in production and RabbitMQ locally.

# ADR-010: Temporal gate result

**Status:** Superseded | **Date:** 2026-06-27 | **Corrected:** 2026-07-02

## Decision record

Temporal was deferred from the production architecture. The earlier record claimed a sub-30-second sweep and a one-line `TEMPORAL_ENABLED` switch; neither is a current supported contract. The obsolete flag and unimplemented stub were removed.

The supported integration seam is `run_optimization_sweep()`. A future Temporal proof of concept may call a complete deterministic sweep as one activity, but it must remain isolated until its retry, state, cost, and operational behavior are proven.

## Current consequences

- No Temporal server is required by the application.
- RabbitMQ workers provide local asynchronous execution.
- SQS/Lambda provides production queued execution.
- Queue retention and DLQ configuration do not by themselves prove application-level retry or durable state.
- Runtime is reported only from retained evidence for a specified revision and environment.
