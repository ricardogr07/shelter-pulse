"""DuckDB persistence for optimization runs and consent records.

Design:
- WAL mode for concurrent read + sequential write safety
- API reads only (GET /runs/recent), workers write only (after sweep)
- DUCKDB_PATH env var configures location (EFS in prod, local volume in docker)
- IP addresses are SHA256-hashed before storage, never stored raw
"""

from __future__ import annotations

import hashlib
import os
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Generator
from uuid import uuid4

import duckdb  # type: ignore[import-untyped]

DUCKDB_PATH = os.getenv("DUCKDB_PATH", "./data/shelterpulse.duckdb")


def _get_db_path() -> str:
    """Get the DuckDB path, reading env var at call time."""
    return os.getenv("DUCKDB_PATH", DUCKDB_PATH)

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS optimization_runs (
    job_id              VARCHAR PRIMARY KEY,
    created_at          TIMESTAMP DEFAULT current_timestamp,
    scenario_name       VARCHAR,
    duration_days       INTEGER,
    housing_capacity    INTEGER,
    isolation_slots     INTEGER,
    vet_tech_fte        DOUBLE,
    intervention_budget DOUBLE,
    mean_intake_per_day DOUBLE,
    kitten_fraction     DOUBLE,
    base_adoption_rate  DOUBLE,
    -- winner allocation
    winner_foster_support      DOUBLE,
    winner_clinic_hours        DOUBLE,
    winner_temporary_isolation DOUBLE,
    winner_adoption_events     DOUBLE,
    -- winner results
    winner_mean_overflow       DOUBLE,
    winner_std_overflow        DOUBLE,
    winner_mean_cost           DOUBLE,
    winner_is_feasible         BOOLEAN,
    winner_ci95_low            DOUBLE,
    winner_ci95_high           DOUBLE,
    -- metadata
    n_candidates        INTEGER,
    n_replications      INTEGER,
    sweep_duration_ms   INTEGER,
    consent_given       BOOLEAN DEFAULT false,
    is_test_data        BOOLEAN DEFAULT false
);

CREATE TABLE IF NOT EXISTS optimization_candidates (
    id                  VARCHAR PRIMARY KEY,
    job_id              VARCHAR NOT NULL,
    rank                INTEGER NOT NULL,
    foster_support      DOUBLE,
    clinic_hours        DOUBLE,
    temporary_isolation DOUBLE,
    adoption_events     DOUBLE,
    mean_overflow_cat_days DOUBLE,
    std_overflow_cat_days  DOUBLE,
    mean_total_cost     DOUBLE,
    is_feasible         BOOLEAN,
    ci95_overflow_low   DOUBLE,
    ci95_overflow_high  DOUBLE,
    ci95_cost_low       DOUBLE,
    ci95_cost_high      DOUBLE
);

CREATE TABLE IF NOT EXISTS consent_records (
    id              VARCHAR PRIMARY KEY,
    created_at      TIMESTAMP DEFAULT current_timestamp,
    session_id      VARCHAR,
    ip_hash         VARCHAR,
    consent_storage BOOLEAN,
    is_test_data    BOOLEAN
);
"""


@contextmanager
def get_connection(path: str | None = None) -> Generator[duckdb.DuckDBPyConnection, None, None]:
    """Open a DuckDB connection with WAL mode.

    Args:
        path: Override database path (useful for tests with temp files).
    """
    db_path = path or _get_db_path()
    # Ensure parent directory exists
    db_dir = os.path.dirname(db_path)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)
    conn = duckdb.connect(db_path)
    try:
        yield conn
    finally:
        conn.close()


def init_schema(path: str | None = None) -> None:
    """Create tables if they don't exist. Call on app startup."""
    with get_connection(path) as conn:
        conn.execute(_SCHEMA_SQL)


def save_run(
    job_id: str,
    scenario: dict[str, Any],
    results: list[dict[str, Any]],
    consent: bool,
    is_test: bool,
    sweep_duration_ms: int = 0,
    path: str | None = None,
) -> None:
    """Persist a complete optimization run with all candidates.

    Only writes if consent=True. This is the primary gate for data storage.
    """
    if not consent:
        return

    with get_connection(path) as conn:
        # The first result is the winner (results are pre-sorted by overflow)
        winner = results[0] if results else {}

        conn.execute(
            """
            INSERT INTO optimization_runs VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?
            )
            """,
            [
                job_id,
                datetime.now(timezone.utc),
                scenario.get("name", "Unknown"),
                scenario.get("duration_days"),
                scenario.get("housing_capacity"),
                scenario.get("isolation_slots"),
                scenario.get("vet_tech_fte"),
                scenario.get("intervention_budget"),
                scenario.get("mean_intake_per_day"),
                scenario.get("kitten_fraction"),
                scenario.get("base_adoption_rate"),
                # winner allocation
                winner.get("foster_support"),
                winner.get("clinic_hours"),
                winner.get("temporary_isolation"),
                winner.get("adoption_events"),
                # winner results
                winner.get("mean_overflow_cat_days"),
                winner.get("std_overflow_cat_days"),
                winner.get("mean_total_cost"),
                winner.get("is_feasible"),
                winner.get("ci95_overflow_low"),
                winner.get("ci95_overflow_high"),
                # metadata
                len(results),
                scenario.get("n_replications"),
                sweep_duration_ms,
                consent,
                is_test,
            ],
        )

        # Store all candidates
        for rank, candidate in enumerate(results, start=1):
            conn.execute(
                """
                INSERT INTO optimization_candidates VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                )
                """,
                [
                    str(uuid4()),
                    job_id,
                    rank,
                    candidate.get("foster_support"),
                    candidate.get("clinic_hours"),
                    candidate.get("temporary_isolation"),
                    candidate.get("adoption_events"),
                    candidate.get("mean_overflow_cat_days"),
                    candidate.get("std_overflow_cat_days"),
                    candidate.get("mean_total_cost"),
                    candidate.get("is_feasible"),
                    candidate.get("ci95_overflow_low"),
                    candidate.get("ci95_overflow_high"),
                    candidate.get("ci95_cost_low"),
                    candidate.get("ci95_cost_high"),
                ],
            )


def get_runs_for_shelter(
    name: str,
    housing_capacity: int,
    isolation_slots: int,
    intervention_budget: float,
    limit: int = 10,
    path: str | None = None,
) -> list[dict[str, Any]]:
    """Fetch recent runs matching a shelter by name + key parameters.

    Matching criteria: exact name (case-insensitive) AND same capacity,
    isolation slots, and budget (within 1% tolerance for floats).
    """
    with get_connection(path) as conn:
        rows = conn.execute(
            """
            SELECT
                job_id, created_at, scenario_name,
                duration_days, housing_capacity, isolation_slots,
                intervention_budget, mean_intake_per_day,
                winner_foster_support, winner_clinic_hours,
                winner_temporary_isolation, winner_adoption_events,
                winner_mean_overflow, winner_is_feasible,
                n_candidates, n_replications
            FROM optimization_runs
            WHERE LOWER(scenario_name) = LOWER(?)
              AND housing_capacity = ?
              AND isolation_slots = ?
              AND ABS(intervention_budget - ?) / GREATEST(intervention_budget, 1) < 0.01
            ORDER BY created_at DESC
            LIMIT ?
            """,
            [name, housing_capacity, isolation_slots, intervention_budget, limit],
        ).fetchall()

        columns = [
            "job_id", "created_at", "scenario_name",
            "duration_days", "housing_capacity", "isolation_slots",
            "intervention_budget", "mean_intake_per_day",
            "winner_foster_support", "winner_clinic_hours",
            "winner_temporary_isolation", "winner_adoption_events",
            "winner_mean_overflow", "winner_is_feasible",
            "n_candidates", "n_replications",
        ]
        return [dict(zip(columns, row)) for row in rows]


def get_candidates_for_run(
    job_id: str,
    path: str | None = None,
) -> list[dict[str, Any]]:
    """Fetch all candidates for a specific optimization run."""
    with get_connection(path) as conn:
        rows = conn.execute(
            """
            SELECT
                rank, foster_support, clinic_hours,
                temporary_isolation, adoption_events,
                mean_overflow_cat_days, std_overflow_cat_days,
                mean_total_cost, is_feasible,
                ci95_overflow_low, ci95_overflow_high
            FROM optimization_candidates
            WHERE job_id = ?
            ORDER BY rank
            """,
            [job_id],
        ).fetchall()

        columns = [
            "rank", "foster_support", "clinic_hours",
            "temporary_isolation", "adoption_events",
            "mean_overflow_cat_days", "std_overflow_cat_days",
            "mean_total_cost", "is_feasible",
            "ci95_overflow_low", "ci95_overflow_high",
        ]
        return [dict(zip(columns, row)) for row in rows]


def log_consent(
    session_id: str,
    ip: str,
    consent: bool,
    is_test: bool,
    path: str | None = None,
) -> None:
    """Record a consent decision. Always logged, even when user declines.

    IP address is SHA256-hashed (truncated to 16 chars) before storage.
    """
    ip_hash = hashlib.sha256(ip.encode()).hexdigest()[:16]
    with get_connection(path) as conn:
        conn.execute(
            """
            INSERT INTO consent_records VALUES (?, ?, ?, ?, ?, ?)
            """,
            [
                str(uuid4()),
                datetime.now(timezone.utc),
                session_id,
                ip_hash,
                consent,
                is_test,
            ],
        )
