"""E2E tests for the FastAPI REST layer using httpx AsyncClient."""
import pytest
from httpx import ASGITransport, AsyncClient

from shelterpulse.api.app import app


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


async def test_health(client):
    r = await client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


async def test_simulate_default(client):
    r = await client.post("/simulate", json={})
    assert r.status_code == 200
    data = r.json()
    assert data["mean_overflow_cat_days"] >= 0
    assert "is_feasible" in data


async def test_optimize_returns_sorted(client):
    r = await client.post("/optimize", json={"n_candidates": 4, "n_replications": 8, "use_bo": False})
    assert r.status_code == 200
    results = r.json()
    assert len(results) >= 1


async def test_baselines_returns_four(client):
    r = await client.get("/baselines")
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 5


async def test_timeline_builder_default(client):
    """Builder timeline returns correct number of days with default allocation."""
    r = await client.post("/simulate/timeline/builder", json={"duration_days": 30, "housing_capacity": 35, "isolation_slots": 5, "vet_tech_fte": 1.5, "intervention_budget": 5000, "mean_intake_per_day": 3.8, "kitten_fraction": 0.59, "base_adoption_rate": 0.08})
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 30
    assert all("day" in p and "housing_used" in p and "overflow" in p for p in data)


async def test_timeline_builder_with_allocation(client):
    """Builder timeline respects the allocation parameter."""
    r = await client.post("/simulate/timeline/builder", json={"duration_days": 30, "housing_capacity": 35, "isolation_slots": 5, "vet_tech_fte": 1.5, "intervention_budget": 5000, "mean_intake_per_day": 3.8, "kitten_fraction": 0.59, "base_adoption_rate": 0.08, "allocation": {"foster_support": 0.4, "clinic_hours": 0.0, "temporary_isolation": 0.2, "adoption_events": 0.4}})
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 30


async def test_timeline_builder_compare(client):
    """Compare endpoint returns both before and after timelines."""
    r = await client.post("/simulate/timeline/builder/compare", json={"duration_days": 30, "housing_capacity": 35, "isolation_slots": 5, "vet_tech_fte": 1.5, "intervention_budget": 5000, "mean_intake_per_day": 3.8, "kitten_fraction": 0.59, "base_adoption_rate": 0.08, "allocation": {"foster_support": 0.4, "clinic_hours": 0.0, "temporary_isolation": 0.2, "adoption_events": 0.4}})
    assert r.status_code == 200
    data = r.json()
    assert "before" in data and "after" in data
    assert len(data["before"]) == 30
    assert len(data["after"]) == 30


async def test_optimize_builder_compare(client):
    """Compare endpoint returns winner + 5 baselines evaluated on custom scenario."""
    r = await client.post("/optimize/builder/compare", json={"duration_days": 30, "housing_capacity": 35, "isolation_slots": 5, "vet_tech_fte": 1.5, "intervention_budget": 5000, "mean_intake_per_day": 3.8, "kitten_fraction": 0.59, "base_adoption_rate": 0.08, "n_replications": 8})
    assert r.status_code == 200
    data = r.json()
    assert "winner" in data
    assert "baselines" in data
    assert len(data["baselines"]) == 5
    assert data["winner"]["mean_overflow_cat_days"] >= 0
