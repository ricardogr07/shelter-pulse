> **SUPERSEDED by [ADR-012](012-queue-abstraction.md).** Temporal was replaced with a queue abstraction (RabbitMQ local, SQS+Lambda prod). Kept for decision trail.

# ADR-004: Gate Temporal Adoption to EOD June 28

**Status:** Superseded by ADR-012 | **Date:** 2026-06-26

## Context

Temporal is well-suited to orchestrating long-running, resumable Monte Carlo + BO sweeps
and is a hackathon sponsor (Technical Execution rubric bonus). However, adopting Temporal
costs an estimated 8–12 h of learning curve that a solo developer at 65 net hours cannot
spend speculatively.

## Decision

`optimize/workflow.py` contains a `TEMPORAL_ENABLED = False` flag. The module implements
both an in-process sweep path (`_inprocess_sweep`) and a Temporal workflow path
(`_temporal_sweep`). The flag switches between them without touching the rest of the codebase.

**Gate rule (scope lock §4):** If the simulation + BO core runs end-to-end on a trusted
baseline by EOD June 28, flip the flag to `True` and enable the Temporal service in
`docker-compose.yml`. If the core is not working by then, leave the flag `False` and
proceed with in-process optimization.

## Consequences

- Temporal adoption is a one-line change + docker-compose profile enable.
- The scaffold (stub workflow, docker-compose service definition) is present from day one,
  so the Jun 28 adoption is low-friction.
- Either outcome has a clean demo narrative (see scope lock §4).
- The core library remains pure and testable regardless of the flag value.
