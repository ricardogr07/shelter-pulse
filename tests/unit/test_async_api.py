"""Tests for async optimization flow: job store, async dispatch, webhooks."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from httpx import ASGITransport, AsyncClient

from shelterpulse.api.app import app
from shelterpulse.queue.job_store import Job, JobStatus, JobStore, job_store


# ── Job Store unit tests ──────────────────────────────────────────────────────


class TestJobStore:
    """Unit tests for the in-memory job store."""

    def test_create_job(self):
        store = JobStore()
        job = store.create("job-1", total=20)
        assert job.job_id == "job-1"
        assert job.status == JobStatus.QUEUED
        assert job.progress_total == 20

    def test_get_existing_job(self):
        store = JobStore()
        store.create("job-2")
        job = store.get("job-2")
        assert job is not None
        assert job.job_id == "job-2"

    def test_get_nonexistent_returns_none(self):
        store = JobStore()
        assert store.get("nonexistent") is None

    def test_update_progress(self):
        store = JobStore()
        store.create("job-3", total=20)
        store.update_progress("job-3", done=5, total=20)
        job = store.get("job-3")
        assert job is not None
        assert job.status == JobStatus.RUNNING
        assert job.progress_done == 5
        assert job.progress_total == 20

    def test_complete_job(self):
        store = JobStore()
        store.create("job-4")
        store.complete("job-4", results=[{"test": "data"}])
        job = store.get("job-4")
        assert job is not None
        assert job.status == JobStatus.COMPLETED
        assert job.results == [{"test": "data"}]

    def test_fail_job(self):
        store = JobStore()
        store.create("job-5")
        store.fail("job-5", error="Something went wrong")
        job = store.get("job-5")
        assert job is not None
        assert job.status == JobStatus.FAILED
        assert job.error == "Something went wrong"

    def test_update_nonexistent_is_safe(self):
        """Operations on missing job_ids don't raise."""
        store = JobStore()
        store.update_progress("missing", 1, 10)
        store.complete("missing", [])
        store.fail("missing", "error")


class TestSweepStale:
    """Unit tests for JobStore.sweep_stale() TTL expiry."""

    def _age(self, store: JobStore, job_id: str, seconds: int) -> None:
        """Backdate a job's updated_at to simulate elapsed time."""
        job = store.get(job_id)
        assert job is not None
        job.updated_at = datetime.now(timezone.utc) - timedelta(seconds=seconds)

    def test_expires_stale_queued_job(self):
        store = JobStore()
        store.create("stale-queued")
        self._age(store, "stale-queued", 301)

        expired = store.sweep_stale(ttl_seconds=300)

        assert expired == 1
        job = store.get("stale-queued")
        assert job is not None
        assert job.status == JobStatus.FAILED
        assert job.error == "Job timed out"

    def test_expires_stale_running_job(self):
        store = JobStore()
        store.create("stale-running")
        store.update_progress("stale-running", 1, 5)
        self._age(store, "stale-running", 301)

        expired = store.sweep_stale(ttl_seconds=300)

        assert expired == 1
        assert store.get("stale-running").status == JobStatus.FAILED

    def test_leaves_recent_jobs_alone(self):
        """Jobs updated within the TTL window are untouched."""
        store = JobStore()
        store.create("fresh-job")
        self._age(store, "fresh-job", 60)

        expired = store.sweep_stale(ttl_seconds=300)

        assert expired == 0
        assert store.get("fresh-job").status == JobStatus.QUEUED

    def test_leaves_completed_and_failed_jobs_alone(self):
        """Sweep only targets queued/running - terminal states are untouched."""
        store = JobStore()
        store.create("done-job")
        store.complete("done-job", [{"ok": True}])
        self._age(store, "done-job", 301)

        expired = store.sweep_stale(ttl_seconds=300)

        assert expired == 0
        assert store.get("done-job").status == JobStatus.COMPLETED

    def test_purges_old_completed_jobs(self):
        """Completed/failed jobs older than the retention window are dropped."""
        store = JobStore()
        store.create("old-completed")
        store.complete("old-completed", [{"ok": True}])
        self._age(store, "old-completed", 1801)

        store.sweep_stale()

        assert store.get("old-completed") is None

    def test_active_count_drops_after_sweep(self):
        """count_active_by_ip no longer counts jobs that timed out."""
        store = JobStore()
        store.create("stuck-job", client_ip="1.2.3.4")
        self._age(store, "stuck-job", 301)

        assert store.count_active_by_ip("1.2.3.4") == 0

    def test_create_triggers_lazy_sweep(self):
        """Calling create() sweeps existing stale jobs first."""
        store = JobStore()
        store.create("old-stuck")
        self._age(store, "old-stuck", 301)

        store.create("new-job")

        assert store.get("old-stuck").status == JobStatus.FAILED

    def test_sweep_notifies_sse_subscribers(self):
        """A subscriber on a timed-out job receives an error event."""
        store = JobStore()
        store.create("sse-timeout-job")
        queue = store.subscribe("sse-timeout-job")
        self._age(store, "sse-timeout-job", 301)

        store.sweep_stale(ttl_seconds=300)

        event = queue.get_nowait()
        assert event["event"] == "error"
        assert event["message"] == "Job timed out"


# ── API endpoint tests (sync mode - default) ─────────────────────────────────


@pytest.fixture
def client():
    """AsyncClient with QUEUE_BACKEND=sync (default behavior)."""
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


class TestOptimizeBuilderSync:
    """Verify /optimize/builder still works in sync mode (default)."""

    async def test_sync_returns_200_with_results(self, client):
        """Default (sync) mode returns 200 with list of results."""
        resp = await client.post("/optimize/builder", json={
            "duration_days": 30,
            "housing_capacity": 20,
            "n_replications": 4,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) > 0
        assert "mean_overflow_cat_days" in data[0]


# ── API endpoint tests (async mode) ──────────────────────────────────────────


@pytest.fixture
def async_client(monkeypatch):
    """AsyncClient with QUEUE_BACKEND=rabbitmq to trigger async path."""
    monkeypatch.setenv("QUEUE_BACKEND", "rabbitmq")
    # Patch the publisher to avoid needing actual RabbitMQ
    from unittest.mock import AsyncMock

    mock_publisher = AsyncMock()
    monkeypatch.setattr("shelterpulse.api.app.get_publisher", lambda: mock_publisher)
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


class TestOptimizeBuilderAsync:
    """Verify /optimize/builder async dispatch behavior."""

    async def test_async_returns_202_with_job_id(self, async_client):
        """Async mode returns 202 with job_id."""
        resp = await async_client.post("/optimize/builder", json={
            "duration_days": 30,
            "housing_capacity": 20,
            "n_replications": 4,
        })
        assert resp.status_code == 202
        data = resp.json()
        assert "job_id" in data
        assert data["status"] == "queued"


class TestJobStatusEndpoints:
    """Test the job status and results polling endpoints."""

    async def test_status_returns_queued(self, client):
        """GET /optimize/{job_id}/status returns current state."""
        job = job_store.create("test-status-job", total=15)
        resp = await client.get("/optimize/test-status-job/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "queued"
        assert data["progress_total"] == 15

    async def test_status_404_for_unknown(self, client):
        """GET /optimize/{job_id}/status returns 404 for unknown job."""
        resp = await client.get("/optimize/unknown-job/status")
        assert resp.status_code == 404

    async def test_results_returns_data_when_complete(self, client):
        """GET /optimize/{job_id}/results returns results after completion."""
        job_store.create("test-results-job")
        job_store.complete("test-results-job", [{"overflow": 10.5}])
        resp = await client.get("/optimize/test-results-job/results")
        assert resp.status_code == 200
        data = resp.json()
        assert data == [{"overflow": 10.5}]

    async def test_results_409_when_not_complete(self, client):
        """GET /optimize/{job_id}/results returns 409 if still running."""
        job_store.create("test-incomplete-job")
        resp = await client.get("/optimize/test-incomplete-job/results")
        assert resp.status_code == 409

    async def test_results_500_when_failed(self, client):
        """GET /optimize/{job_id}/results returns 500 if job failed."""
        job_store.create("test-failed-job")
        job_store.fail("test-failed-job", "BO diverged")
        resp = await client.get("/optimize/test-failed-job/results")
        assert resp.status_code == 500


class TestInternalWebhooks:
    """Test the internal webhook endpoints called by workers."""

    async def test_progress_webhook(self, client):
        """POST /internal/jobs/{id}/progress updates job state."""
        job_store.create("webhook-progress-job")
        resp = await client.post(
            "/internal/jobs/webhook-progress-job/progress",
            json={"done": 7, "total": 20},
            headers={"X-Internal-Key": "dev-key-123"},
        )
        assert resp.status_code == 200
        job = job_store.get("webhook-progress-job")
        assert job is not None
        assert job.progress_done == 7
        assert job.status == JobStatus.RUNNING

    async def test_complete_webhook(self, client):
        """POST /internal/jobs/{id}/complete marks job done."""
        job_store.create("webhook-complete-job")
        resp = await client.post(
            "/internal/jobs/webhook-complete-job/complete",
            json={"results": [{"overflow": 0.0}]},
            headers={"X-Internal-Key": "dev-key-123"},
        )
        assert resp.status_code == 200
        job = job_store.get("webhook-complete-job")
        assert job is not None
        assert job.status == JobStatus.COMPLETED
        assert job.results == [{"overflow": 0.0}]

    async def test_fail_webhook(self, client):
        """POST /internal/jobs/{id}/fail marks job as failed."""
        job_store.create("webhook-fail-job")
        resp = await client.post(
            "/internal/jobs/webhook-fail-job/fail",
            json={"error": "Worker crashed"},
            headers={"X-Internal-Key": "dev-key-123"},
        )
        assert resp.status_code == 200
        job = job_store.get("webhook-fail-job")
        assert job is not None
        assert job.status == JobStatus.FAILED
        assert job.error == "Worker crashed"

    async def test_webhook_rejects_bad_key(self, client):
        """Webhooks reject requests without valid X-Internal-Key."""
        job_store.create("webhook-auth-job")
        resp = await client.post(
            "/internal/jobs/webhook-auth-job/complete",
            json={"results": []},
            headers={"X-Internal-Key": "wrong-key"},
        )
        assert resp.status_code == 403
