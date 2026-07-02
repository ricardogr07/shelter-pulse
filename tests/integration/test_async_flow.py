"""Integration test for the full async optimization flow via docker-compose.

Requires: docker compose up (api + rabbitmq + worker) running on localhost.
Run with: pytest tests/integration/ -v

This test verifies the end-to-end async flow:
1. POST /optimize/builder -> 202 with job_id
2. Worker picks up job from RabbitMQ
3. Worker calls webhook with results
4. GET /optimize/{job_id}/status -> completed
5. GET /optimize/{job_id}/results -> actual optimization results
"""

from __future__ import annotations

import time

import httpx
import pytest

API_URL = "http://localhost:8000"


@pytest.fixture
def client():
    """httpx client targeting the local docker-compose API."""
    return httpx.Client(base_url=API_URL, timeout=120.0)


def _wait_for_api(client: httpx.Client, timeout: float = 30.0) -> bool:
    """Wait for the API to be healthy."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            r = client.get("/health")
            if r.status_code == 200:
                return True
        except httpx.ConnectError:
            pass
        time.sleep(1)
    return False


class TestAsyncOptimizationFlow:
    """Full end-to-end test of async optimization via RabbitMQ worker."""

    def test_api_is_healthy(self, client):
        """Verify the API is running and healthy."""
        assert _wait_for_api(client), "API not reachable at localhost:8000"
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"

    def test_async_optimize_full_flow(self, client):
        """POST optimize -> poll status -> get results (full async flow)."""
        if not _wait_for_api(client):
            pytest.skip("API not reachable - docker compose not running")

        # 1. Submit optimization job
        resp = client.post("/optimize/builder", json={
            "duration_days": 30,
            "housing_capacity": 20,
            "n_replications": 4,
        })
        assert resp.status_code == 202, f"Expected 202, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert "job_id" in data
        job_id = data["job_id"]
        assert data["status"] == "queued"

        # 2. Poll status until completed (timeout: 90s for BO sweep)
        deadline = time.time() + 90.0
        final_status = None
        while time.time() < deadline:
            status_resp = client.get(f"/optimize/{job_id}/status")
            assert status_resp.status_code == 200
            status_data = status_resp.json()
            final_status = status_data["status"]
            if final_status in ("completed", "failed"):
                break
            time.sleep(2)

        assert final_status == "completed", f"Job did not complete: {final_status}"

        # 3. Retrieve results
        results_resp = client.get(f"/optimize/{job_id}/results")
        assert results_resp.status_code == 200
        results = results_resp.json()
        assert isinstance(results, list)
        assert len(results) > 0
        assert "mean_overflow_cat_days" in results[0]
        assert "foster_support" in results[0]

    def test_job_status_404_for_unknown(self, client):
        """Verify unknown job_id returns 404."""
        if not _wait_for_api(client):
            pytest.skip("API not reachable")
        resp = client.get("/optimize/unknown-id-123/status")
        assert resp.status_code == 404
