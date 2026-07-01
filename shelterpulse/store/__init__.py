"""DuckDB persistence layer for ShelterPulse optimization runs."""

try:
    from shelterpulse.store.duckdb_store import (
        get_runs_for_shelter,
        init_schema,
        log_consent,
        save_run,
    )
except ImportError:
    # duckdb not installed (store extra not included)
    # Provide no-op stubs so the app runs without persistence
    def init_schema(path=None):  # type: ignore[misc]
        pass

    def save_run(job_id=None, scenario=None, results=None, consent=False, is_test=False, sweep_duration_ms=0, path=None):  # type: ignore[misc]
        pass

    def get_runs_for_shelter(name="", housing_capacity=0, isolation_slots=0, intervention_budget=0.0, limit=10, path=None):  # type: ignore[misc]
        return []

    def log_consent(session_id="", ip="", consent=False, is_test=False, path=None):  # type: ignore[misc]
        pass


__all__ = ["init_schema", "save_run", "get_runs_for_shelter", "log_consent"]
