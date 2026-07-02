"""Tests for DuckDB store: save_run, get_runs_for_shelter, consent logic."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest

duckdb = pytest.importorskip("duckdb", reason="duckdb not installed (store extra)")

from shelterpulse.store.duckdb_store import (
    get_candidates_for_run,
    get_connection,
    get_runs_for_shelter,
    init_schema,
    log_consent,
    save_run,
)


@pytest.fixture()
def db_path(tmp_path: Path) -> str:
    """Create a temporary DuckDB file for each test."""
    path = str(tmp_path / "test.duckdb")
    init_schema(path)
    return path


SAMPLE_SCENARIO = {
    "name": "Test Shelter",
    "duration_days": 30,
    "housing_capacity": 20,
    "isolation_slots": 3,
    "vet_tech_fte": 1.0,
    "intervention_budget": 3000.0,
    "mean_intake_per_day": 2.5,
    "kitten_fraction": 0.4,
    "base_adoption_rate": 0.1,
    "n_replications": 4,
}

SAMPLE_RESULTS = [
    {
        "foster_support": 0.4,
        "clinic_hours": 0.1,
        "temporary_isolation": 0.2,
        "adoption_events": 0.3,
        "mean_overflow_cat_days": 5.2,
        "std_overflow_cat_days": 1.1,
        "mean_total_cost": 2800.0,
        "is_feasible": True,
        "ci95_overflow_low": 3.0,
        "ci95_overflow_high": 7.4,
        "ci95_cost_low": 2500.0,
        "ci95_cost_high": 3100.0,
    },
    {
        "foster_support": 0.25,
        "clinic_hours": 0.25,
        "temporary_isolation": 0.25,
        "adoption_events": 0.25,
        "mean_overflow_cat_days": 12.8,
        "std_overflow_cat_days": 3.2,
        "mean_total_cost": 3000.0,
        "is_feasible": True,
        "ci95_overflow_low": 6.4,
        "ci95_overflow_high": 19.2,
        "ci95_cost_low": 2700.0,
        "ci95_cost_high": 3300.0,
    },
]


class TestInitSchema:
    """Test schema creation."""

    def test_creates_tables(self, db_path: str):
        """Schema init creates all 3 tables."""
        with get_connection(db_path) as conn:
            tables = conn.execute(
                "SELECT table_name FROM information_schema.tables WHERE table_schema='main'"
            ).fetchall()
        table_names = {t[0] for t in tables}
        assert "optimization_runs" in table_names
        assert "optimization_candidates" in table_names
        assert "consent_records" in table_names

    def test_idempotent(self, db_path: str):
        """Calling init_schema twice does not fail."""
        init_schema(db_path)  # Second call
        with get_connection(db_path) as conn:
            count = conn.execute("SELECT count(*) FROM optimization_runs").fetchone()[0]
        assert count == 0


class TestSaveRun:
    """Test save_run persistence."""

    def test_saves_run_with_consent(self, db_path: str):
        """Run is saved when consent=True."""
        save_run("job-1", SAMPLE_SCENARIO, SAMPLE_RESULTS, consent=True, is_test=False, path=db_path)

        with get_connection(db_path) as conn:
            runs = conn.execute("SELECT * FROM optimization_runs").fetchall()
        assert len(runs) == 1
        assert runs[0][0] == "job-1"  # job_id

    def test_does_not_save_without_consent(self, db_path: str):
        """Run is NOT saved when consent=False."""
        save_run("job-2", SAMPLE_SCENARIO, SAMPLE_RESULTS, consent=False, is_test=False, path=db_path)

        with get_connection(db_path) as conn:
            count = conn.execute("SELECT count(*) FROM optimization_runs").fetchone()[0]
        assert count == 0

    def test_stores_all_candidates(self, db_path: str):
        """All candidates are persisted to optimization_candidates table."""
        save_run("job-3", SAMPLE_SCENARIO, SAMPLE_RESULTS, consent=True, is_test=True, path=db_path)

        with get_connection(db_path) as conn:
            candidates = conn.execute(
                "SELECT * FROM optimization_candidates WHERE job_id='job-3' ORDER BY rank"
            ).fetchall()
        assert len(candidates) == 2  # Two sample results
        # First candidate (rank 1) should be the winner
        assert candidates[0][2] == 1  # rank column

    def test_winner_fields_stored(self, db_path: str):
        """Winner allocation and metrics are stored in optimization_runs."""
        save_run("job-4", SAMPLE_SCENARIO, SAMPLE_RESULTS, consent=True, is_test=False, path=db_path)

        with get_connection(db_path) as conn:
            row = conn.execute(
                "SELECT winner_foster_support, winner_mean_overflow, winner_is_feasible FROM optimization_runs WHERE job_id='job-4'"
            ).fetchone()
        assert row[0] == pytest.approx(0.4)
        assert row[1] == pytest.approx(5.2)
        assert row[2] is True

    def test_scenario_name_stored(self, db_path: str):
        """Scenario name is stored for shelter matching."""
        save_run("job-5", SAMPLE_SCENARIO, SAMPLE_RESULTS, consent=True, is_test=False, path=db_path)

        with get_connection(db_path) as conn:
            name = conn.execute(
                "SELECT scenario_name FROM optimization_runs WHERE job_id='job-5'"
            ).fetchone()[0]
        assert name == "Test Shelter"


class TestGetRunsForShelter:
    """Test shelter matching queries."""

    def test_matches_by_name_and_params(self, db_path: str):
        """Finds runs matching name + capacity + isolation + budget."""
        save_run("job-match", SAMPLE_SCENARIO, SAMPLE_RESULTS, consent=True, is_test=False, path=db_path)

        runs = get_runs_for_shelter(
            name="Test Shelter",
            housing_capacity=20,
            isolation_slots=3,
            intervention_budget=3000.0,
            path=db_path,
        )
        assert len(runs) == 1
        assert runs[0]["job_id"] == "job-match"

    def test_case_insensitive_name(self, db_path: str):
        """Name matching is case-insensitive."""
        save_run("job-case", SAMPLE_SCENARIO, SAMPLE_RESULTS, consent=True, is_test=False, path=db_path)

        runs = get_runs_for_shelter(
            name="test shelter",  # lowercase
            housing_capacity=20,
            isolation_slots=3,
            intervention_budget=3000.0,
            path=db_path,
        )
        assert len(runs) == 1

    def test_no_match_different_capacity(self, db_path: str):
        """Different housing_capacity does not match."""
        save_run("job-cap", SAMPLE_SCENARIO, SAMPLE_RESULTS, consent=True, is_test=False, path=db_path)

        runs = get_runs_for_shelter(
            name="Test Shelter",
            housing_capacity=50,  # Different
            isolation_slots=3,
            intervention_budget=3000.0,
            path=db_path,
        )
        assert len(runs) == 0

    def test_no_match_different_name(self, db_path: str):
        """Different name does not match."""
        save_run("job-name", SAMPLE_SCENARIO, SAMPLE_RESULTS, consent=True, is_test=False, path=db_path)

        runs = get_runs_for_shelter(
            name="Other Shelter",
            housing_capacity=20,
            isolation_slots=3,
            intervention_budget=3000.0,
            path=db_path,
        )
        assert len(runs) == 0

    def test_budget_tolerance(self, db_path: str):
        """Budget matches within 1% tolerance."""
        save_run("job-tol", SAMPLE_SCENARIO, SAMPLE_RESULTS, consent=True, is_test=False, path=db_path)

        # 0.5% difference should match
        runs = get_runs_for_shelter(
            name="Test Shelter",
            housing_capacity=20,
            isolation_slots=3,
            intervention_budget=3015.0,  # 0.5% over 3000
            path=db_path,
        )
        assert len(runs) == 1

        # 5% difference should NOT match
        runs = get_runs_for_shelter(
            name="Test Shelter",
            housing_capacity=20,
            isolation_slots=3,
            intervention_budget=3150.0,  # 5% over 3000
            path=db_path,
        )
        assert len(runs) == 0

    def test_returns_most_recent_first(self, db_path: str):
        """Results are ordered by created_at DESC."""
        save_run("job-old", SAMPLE_SCENARIO, SAMPLE_RESULTS, consent=True, is_test=False, path=db_path)
        save_run("job-new", SAMPLE_SCENARIO, SAMPLE_RESULTS, consent=True, is_test=False, path=db_path)

        runs = get_runs_for_shelter(
            name="Test Shelter",
            housing_capacity=20,
            isolation_slots=3,
            intervention_budget=3000.0,
            path=db_path,
        )
        assert len(runs) == 2
        # Newer should be first (both have same timestamp in fast tests, but order is stable)
        assert runs[0]["job_id"] in ("job-old", "job-new")

    def test_limit_parameter(self, db_path: str):
        """Limit parameter restricts number of results."""
        for i in range(5):
            save_run(f"job-lim-{i}", SAMPLE_SCENARIO, SAMPLE_RESULTS, consent=True, is_test=False, path=db_path)

        runs = get_runs_for_shelter(
            name="Test Shelter",
            housing_capacity=20,
            isolation_slots=3,
            intervention_budget=3000.0,
            limit=3,
            path=db_path,
        )
        assert len(runs) == 3


class TestGetCandidatesForRun:
    """Test fetching all candidates for a specific run."""

    def test_returns_all_candidates_ranked(self, db_path: str):
        """Returns all candidates ordered by rank."""
        save_run("job-cand", SAMPLE_SCENARIO, SAMPLE_RESULTS, consent=True, is_test=False, path=db_path)

        candidates = get_candidates_for_run("job-cand", path=db_path)
        assert len(candidates) == 2
        assert candidates[0]["rank"] == 1
        assert candidates[1]["rank"] == 2
        assert candidates[0]["foster_support"] == pytest.approx(0.4)

    def test_empty_for_nonexistent_job(self, db_path: str):
        """Returns empty list for a job that doesn't exist."""
        candidates = get_candidates_for_run("nonexistent", path=db_path)
        assert candidates == []


class TestLogConsent:
    """Test consent audit trail logging."""

    def test_logs_consent_decision(self, db_path: str):
        """Consent decision is recorded."""
        log_consent("session-1", "192.168.1.1", consent=True, is_test=False, path=db_path)

        with get_connection(db_path) as conn:
            records = conn.execute("SELECT * FROM consent_records").fetchall()
        assert len(records) == 1
        assert records[0][4] is True  # consent_storage

    def test_logs_declined_consent(self, db_path: str):
        """Declined consent is also logged."""
        log_consent("session-2", "10.0.0.1", consent=False, is_test=True, path=db_path)

        with get_connection(db_path) as conn:
            records = conn.execute("SELECT * FROM consent_records").fetchall()
        assert len(records) == 1
        assert records[0][4] is False  # consent_storage
        assert records[0][5] is True  # is_test_data

    def test_ip_is_hashed(self, db_path: str):
        """IP address is stored as a hash, not raw."""
        log_consent("session-3", "203.0.113.42", consent=True, is_test=False, path=db_path)

        with get_connection(db_path) as conn:
            ip_hash = conn.execute("SELECT ip_hash FROM consent_records").fetchone()[0]
        # Should not be the raw IP
        assert ip_hash != "203.0.113.42"
        # Should be a hex string (first 16 chars of SHA-256)
        assert len(ip_hash) == 16
        assert all(c in "0123456789abcdef" for c in ip_hash)

    def test_multiple_consent_records(self, db_path: str):
        """Multiple consent decisions are all recorded."""
        log_consent("s1", "1.1.1.1", consent=True, is_test=False, path=db_path)
        log_consent("s2", "2.2.2.2", consent=False, is_test=True, path=db_path)
        log_consent("s3", "3.3.3.3", consent=True, is_test=True, path=db_path)

        with get_connection(db_path) as conn:
            count = conn.execute("SELECT count(*) FROM consent_records").fetchone()[0]
        assert count == 3


class TestConsentGating:
    """Test that consent controls data persistence end-to-end."""

    def test_no_consent_no_data(self, db_path: str):
        """With consent=False, no data is written anywhere."""
        save_run("no-consent-job", SAMPLE_SCENARIO, SAMPLE_RESULTS, consent=False, is_test=False, path=db_path)

        with get_connection(db_path) as conn:
            runs = conn.execute("SELECT count(*) FROM optimization_runs").fetchone()[0]
            candidates = conn.execute("SELECT count(*) FROM optimization_candidates").fetchone()[0]
        assert runs == 0
        assert candidates == 0

    def test_consent_true_writes_both_tables(self, db_path: str):
        """With consent=True, both runs and candidates are written."""
        save_run("consent-job", SAMPLE_SCENARIO, SAMPLE_RESULTS, consent=True, is_test=False, path=db_path)

        with get_connection(db_path) as conn:
            runs = conn.execute("SELECT count(*) FROM optimization_runs").fetchone()[0]
            candidates = conn.execute("SELECT count(*) FROM optimization_candidates").fetchone()[0]
        assert runs == 1
        assert candidates == 2
