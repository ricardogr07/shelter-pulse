> **SUPERSEDED by [ADR-012](012-queue-abstraction.md).** Temporal is not part of the current production or local runtime.

# ADR-004: Gate Temporal adoption

**Status:** Superseded | **Date:** 2026-06-26 | **Corrected:** 2026-07-02

## Context

Temporal was considered for long-running, resumable optimization workflows, but adopting and operating it during the initial implementation would have expanded scope before the simulation and optimizer contracts were stable.

## Historical decision

Defer Temporal and preserve a direct optimization seam that other execution adapters can call. An early flag/stub suggested Temporal could be enabled with a one-line switch; that claim was never implemented and the dead scaffold has been removed.

## Current boundary

- `run_optimization_sweep()` remains independent of API and queue transports.
- Production queued execution is SQS/Lambda; local queued execution is RabbitMQ.
- Any Temporal work is an isolated capability demonstration until a separate ADR approves production adoption.
