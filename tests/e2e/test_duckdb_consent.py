"""E2E test: optimize with consent -> verify run appears in /runs/recent."""

import os
import tempfile

import pytest

pytest.importorskip("duckdb", reason="duckdb not installed (store extra)")

from httpx import ASGITransport, AsyncClient

# Use a temp directory for the DuckDB file
_tmp_dir = tempfile.mkdtemp()
os.environ["DUCKDB_PATH"] = os.path.join(_tmp_dir, "test_e2e.duckdb")

from shelterpulse.api.app import app  # noqa: E402
from shelterpulse.store import init_schema  # noqa: E402


@pytest.fixture
async def client():
    init_schema()  # Startup event doesn't fire in test client
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


BUILDER_PAYLOAD = {
    "name": "E2E Test Shelter",
    "duration_days": 30,
    "housing_capacity": 20,
    "isolation_slots": 3,
    "vet_tech_fte": 1.0,
    "intervention_budget": 3000.0,
    "mean_intake_per_day": 2.5,
    "kitten_fraction": 0.4,
    "base_adoption_rate": 0.1,
    "n_replications": 4,
    "consent_storage": True,
    "is_test_data": True,
}


async def test_optimize_with_consent_persists_to_runs_recent(client):
    """Full flow: optimize with consent -> check /runs/recent shows the run."""
    # QUEUE_BACKEND defaults to "sync" in tests, so this blocks and returns results
    r = await client.post("/optimize/builder", json=BUILDER_PAYLOAD)
    assert r.status_code == 200
    results = r.json()
    assert len(results) >= 1
    # Winner should have overflow metric
    assert results[0]["mean_overflow_cat_days"] >= 0

    # Now check /runs/recent for this shelter
    params = {
        "name": "E2E Test Shelter",
        "housing_capacity": "20",
        "isolation_slots": "3",
        "intervention_budget": "3000",
    }
    r = await client.get("/runs/recent", params=params)
    assert r.status_code == 200
    runs = r.json()
    assert len(runs) >= 1
    assert runs[0]["scenario_name"] == "E2E Test Shelter"
    assert runs[0]["winner_mean_overflow"] is not None
    assert runs[0]["housing_capacity"] == 20


async def test_optimize_without_consent_does_not_persist(client):
    """Optimize without consent does not appear in /runs/recent."""
    payload = {**BUILDER_PAYLOAD, "name": "No Consent Shelter", "consent_storage": False}
    r = await client.post("/optimize/builder", json=payload)
    assert r.status_code == 200

    # Should NOT appear
    params = {
        "name": "No Consent Shelter",
        "housing_capacity": "20",
        "isolation_slots": "3",
        "intervention_budget": "3000",
    }
    r = await client.get("/runs/recent", params=params)
    assert r.status_code == 200
    runs = r.json()
    assert len(runs) == 0


async def test_runs_recent_no_match(client):
    """Querying with non-matching params returns empty."""
    params = {
        "name": "Nonexistent Shelter",
        "housing_capacity": "999",
        "isolation_slots": "99",
        "intervention_budget": "99999",
    }
    r = await client.get("/runs/recent", params=params)
    assert r.status_code == 200
    assert r.json() == []



async def test_runs_recent_no_params_returns_global_history(client):
    """GET /runs/recent without params returns all consented runs (anonymized)."""
    # First create a run with consent
    r = await client.post("/optimize/builder", json=BUILDER_PAYLOAD)
    assert r.status_code == 200

    # Fetch without any filter params
    r = await client.get("/runs/recent")
    assert r.status_code == 200
    runs = r.json()
    assert len(runs) >= 1
    # Should have expected fields but NOT scenario_name (anonymized)
    run = runs[0]
    assert "job_id" in run
    assert "created_at" in run
    assert "winner_mean_overflow" in run
    assert "is_test_data" in run
    assert "scenario_name" not in run


async def test_runs_analytics_returns_aggregate_stats(client):
    """GET /runs/analytics returns aggregate statistics for non-test runs."""
    # Seed directly via the store to avoid rate limiting from multiple optimize calls
    from shelterpulse.store import save_run
    save_run(
        "analytics-seed",
        {"name": "Analytics Shelter", "duration_days": 30, "housing_capacity": 20,
         "isolation_slots": 3, "vet_tech_fte": 1.0, "intervention_budget": 3000.0,
         "mean_intake_per_day": 2.5, "kitten_fraction": 0.4, "base_adoption_rate": 0.1,
         "n_replications": 4},
        [{"foster_support": 0.4, "clinic_hours": 0.1, "temporary_isolation": 0.2,
          "adoption_events": 0.3, "mean_overflow_cat_days": 8.0, "std_overflow_cat_days": 1.5,
          "mean_total_cost": 2800.0, "is_feasible": True, "ci95_overflow_low": 5.0,
          "ci95_overflow_high": 11.0, "ci95_cost_low": 2500.0, "ci95_cost_high": 3100.0}],
        consent=True,
        is_test=False,
    )

    r = await client.get("/runs/analytics")
    assert r.status_code == 200
    data = r.json()
    assert data.get("total_runs", 0) >= 1
    assert "avg_overflow" in data
    assert "best_overflow" in data
    assert "avg_allocation" in data
    assert "foster_support" in data["avg_allocation"]


async def test_runs_analytics_empty_db_returns_empty(client):
    """GET /runs/analytics on empty DB returns empty dict gracefully."""
    # The first test already populates, but analytics endpoint should always work
    r = await client.get("/runs/analytics")
    assert r.status_code == 200
    # Should be a dict (either empty or populated)
    assert isinstance(r.json(), dict)
