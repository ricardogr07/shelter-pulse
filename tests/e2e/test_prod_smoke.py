"""Production smoke test for the async optimization job lifecycle.

Unlike tests/e2e/test_api.py (in-process ASGI transport), this hits a real
deployed URL end-to-end: POST /optimize/builder -> SQS -> Lambda -> webhook
-> job_store -> GET /optimize/{id}/results. This is the exact chain that
broke in production (see docs/adr/014-async-worker-production-hardening.md)
and that no other test in this repo exercises against real infrastructure.

Requires SMOKE_BASE_URL (e.g. https://shelter-pulse.com) - skipped entirely
if unset, so this never accidentally runs against localhost or CI's
in-process app.
"""
from __future__ import annotations

import asyncio
import os

import httpx
import pytest

SMOKE_BASE_URL = os.getenv("SMOKE_BASE_URL", "").rstrip("/")

pytestmark = pytest.mark.skipif(
    not SMOKE_BASE_URL, reason="SMOKE_BASE_URL not set - skipping live prod smoke test"
)

_POLL_INTERVAL_SECONDS = 5
_POLL_TIMEOUT_SECONDS = 240  # prod sweeps run 30s-3min per docs/architecture/async-workers.md

_BUILDER_BODY = {
    "duration_days": 30,
    "housing_capacity": 20,
    "isolation_slots": 5,
    "vet_tech_fte": 1.5,
    "intervention_budget": 5000,
    "mean_intake_per_day": 3.8,
    "kitten_fraction": 0.59,
    "base_adoption_rate": 0.08,
    "n_replications": 8,
    "consent_storage": False,  # keep DuckDB clean - matches manual verification during ADR-014
    "is_test_data": True,
    "name": "prod-smoke-test",
}


@pytest.fixture
async def client():
    async with httpx.AsyncClient(base_url=f"{SMOKE_BASE_URL}/api", timeout=30) as c:
        yield c


async def test_optimize_builder_async_lifecycle(client):
    """Full async chain: dispatch -> poll -> results, against real infra.

    A 200 here (instead of 202) would mean QUEUE_BACKEND silently reverted
    to sync in prod - fail on that just as hard as an actual error, since it
    means the async pipeline isn't being exercised at all.
    """
    dispatch = await client.post("/optimize/builder", json=_BUILDER_BODY)
    assert dispatch.status_code == 202, (
        f"Expected 202 (async dispatch), got {dispatch.status_code}: {dispatch.text}"
    )
    job_id = dispatch.json()["job_id"]

    elapsed = 0
    status = "queued"
    last_body: dict = {}
    while elapsed < _POLL_TIMEOUT_SECONDS:
        resp = await client.get(f"/optimize/{job_id}/status")
        assert resp.status_code == 200, f"Status poll failed for {job_id}: {resp.status_code} {resp.text}"
        last_body = resp.json()
        status = last_body["status"]
        if status in ("completed", "failed"):
            break
        await asyncio.sleep(_POLL_INTERVAL_SECONDS)
        elapsed += _POLL_INTERVAL_SECONDS

    assert status == "completed", (
        f"Job {job_id} did not complete within {_POLL_TIMEOUT_SECONDS}s "
        f"(last status: {status}, body: {last_body})"
    )

    results = await client.get(f"/optimize/{job_id}/results")
    assert results.status_code == 200, f"Results fetch failed for {job_id}: {results.status_code} {results.text}"
    data = results.json()
    assert len(data) >= 1, f"Job {job_id} completed but returned no results"
    assert all("mean_overflow_cat_days" in r for r in data), (
        f"Job {job_id} results missing expected fields: {data}"
    )
