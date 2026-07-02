# ADR-013: DuckDB over ClickHouse for Optimization Run Persistence

## Status

Accepted (2026-07-01)

## Context

We need to persist optimization run results for analytics and run history.
Users should be able to see previous results when returning to the same shelter configuration.
The storage layer must be shared between the API (reads) and workers (writes).

Options evaluated:
1. **ClickHouse Cloud** - Managed OLAP database
2. **TimescaleDB** - PostgreSQL with time-series extensions
3. **DuckDB on EFS** - Embedded columnar OLAP
4. **SQLite on EFS** - Embedded row-oriented database

## Decision

DuckDB on AWS EFS (Elastic File System).

## Rationale

| Criterion | DuckDB | ClickHouse Cloud | TimescaleDB | SQLite |
|-----------|--------|------------------|-------------|--------|
| Monthly cost | $0 (EFS storage only) | $66+ | $30+ (managed) | $0 |
| Infrastructure | None (embedded) | Separate server | Separate server | None |
| Analytical queries | Columnar, fast aggregation | Excellent | Good | Slow for analytics |
| Concurrency model | WAL (1 writer + N readers) | Full MVCC | Full MVCC | WAL (same) |
| Deployment complexity | Zero | High (network, auth) | Medium | Zero |
| Volume justification | No (< 1000 rows/day) | Overkill | Overkill | Adequate |

Key factors:
- **Volume does not justify a separate server.** Expected write volume is < 100 optimization runs per day. ClickHouse is designed for millions of inserts per second.
- **$0/month vs $66+/month.** EFS storage is $0.03/GB/month; we will use < 100MB.
- **Same EFS persistence story as the rest of the stack.** API and worker already share an EFS mount; DuckDB file lives there.
- **Columnar advantage over SQLite.** Future aggregate queries (average overflow by shelter size, best allocation patterns) benefit from columnar storage.
- **WAL mode is sufficient.** API reads only, worker writes only, one job at a time per SQS message visibility. No write contention.

## Consequences

- No additional infrastructure to provision or maintain
- DuckDB is an optional dependency (`store` extra in pyproject.toml)
- If we ever outgrow single-file storage (unlikely), migration to ClickHouse is straightforward since the schema is simple
- Must ensure only one writer at a time (enforced by SQS message visibility timeout and single RabbitMQ consumer)
