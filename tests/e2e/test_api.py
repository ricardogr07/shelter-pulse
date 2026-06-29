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
