# ADR-003: Use SimPy for Discrete-Event Simulation

**Status:** Accepted | **Date:** 2026-06-26

## Context

The cat-shelter flow (intake → assessment → medical → isolation → housing → foster →
adoption-ready → adopted/transferred) is naturally modelled as a discrete-event system:
cats arrive at random times, compete for finite resources (staff hours, isolation rooms,
foster slots), and wait in queues when resources are unavailable.

## Decision

Use SimPy 4 as the discrete-event simulation engine. SimPy is a process-based DES library
that models resources, queues, and time progression without a dedicated simulation server.
It runs in-process, which keeps the core library pure and testable.

## Consequences

- Well-understood API; queue-sanity tests can compare SimPy output to M/M/1 analytical results.
- Pure Python — no native extensions required in CI or Docker.
- Single-threaded by design: parallelism for Monte Carlo is achieved by running multiple
  independent SimPy environments (one per replication), not by threading within one simulation.
- Not a general agent-based framework; adequate for the locked cat-shelter flow.
