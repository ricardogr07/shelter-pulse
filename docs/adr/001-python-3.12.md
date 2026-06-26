# ADR-001: Use Python 3.12

**Status:** Accepted | **Date:** 2026-06-26

## Context

The project requires a single language across the simulation core, REST API, and CLI. The
developer already has Python 3.12.6 installed locally. The upstream dependencies (SimPy 4,
Pydantic v2, FastAPI, JAX) all support 3.12. Python 3.14 is the system default but is newer
than needed and less battle-tested with JAX.

## Decision

Pin to Python 3.12 via `.python-version`. All CI runners use `python-version: "3.12"`.

## Consequences

- Full compatibility with SimPy, Pydantic v2, JAX/jaxbo, FastAPI, Typer, and the full test stack.
- uv resolves the 3.12 interpreter directly, consistent between dev and CI.
- If a future dependency requires 3.13+, the pin is the single place to update.
