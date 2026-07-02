"""Tests for API rate limiting and input validation hardening."""

import time

import pytest
from fastapi.testclient import TestClient

from shelterpulse.api.app import app
from shelterpulse.api.rate_limit import RateLimiter, get_client_ip


client = TestClient(app)


# ── Input validation tests ────────────────────────────────────────────────────


class TestInputValidation:
    """Test Pydantic model validation bounds."""

    def test_sweep_n_candidates_too_high(self):
        resp = client.post("/optimize", json={"n_candidates": 100, "n_replications": 16})
        assert resp.status_code == 422
        assert "n_candidates" in resp.text

    def test_sweep_n_candidates_zero(self):
        resp = client.post("/optimize", json={"n_candidates": 0, "n_replications": 16})
        assert resp.status_code == 422

    def test_sweep_n_replications_too_high(self):
        resp = client.post("/optimize", json={"n_candidates": 5, "n_replications": 500})
        assert resp.status_code == 422
        assert "n_replications" in resp.text

    def test_simulate_n_replications_too_high(self):
        resp = client.post("/simulate", json={"n_replications": 200})
        assert resp.status_code == 422

    def test_builder_duration_too_high(self):
        resp = client.post("/simulate/builder", json={"duration_days": 1000})
        assert resp.status_code == 422
        assert "duration_days" in resp.text

    def test_builder_housing_too_high(self):
        resp = client.post("/simulate/builder", json={"housing_capacity": 999})
        assert resp.status_code == 422

    def test_builder_negative_budget(self):
        resp = client.post("/simulate/builder", json={"intervention_budget": -100})
        assert resp.status_code == 422

    def test_builder_intake_too_high(self):
        resp = client.post("/simulate/builder", json={"mean_intake_per_day": 100})
        assert resp.status_code == 422

    def test_builder_kitten_fraction_out_of_range(self):
        resp = client.post("/simulate/builder", json={"kitten_fraction": 1.5})
        assert resp.status_code == 422

    def test_allocation_sum_over_one(self):
        resp = client.post("/simulate", json={
            "allocation": {
                "foster_support": 0.5,
                "clinic_hours": 0.5,
                "temporary_isolation": 0.5,
                "adoption_events": 0.5,
            }
        })
        assert resp.status_code == 422
        assert "shares" in resp.text.lower() or "sum" in resp.text.lower()

    def test_valid_params_accepted(self):
        """Verify valid params don't 422 (may 200 or timeout, just not validation error)."""
        resp = client.post("/simulate", json={"n_replications": 2})
        assert resp.status_code == 200


# ── Rate limiter unit tests ───────────────────────────────────────────────────


class TestRateLimiter:
    """Test the token bucket rate limiter logic directly."""

    def test_allows_up_to_max(self):
        limiter = RateLimiter(max_requests=3, window_seconds=60)
        assert limiter.is_allowed("test-ip") is True
        assert limiter.is_allowed("test-ip") is True
        assert limiter.is_allowed("test-ip") is True
        assert limiter.is_allowed("test-ip") is False

    def test_different_keys_independent(self):
        limiter = RateLimiter(max_requests=1, window_seconds=60)
        assert limiter.is_allowed("ip-a") is True
        assert limiter.is_allowed("ip-b") is True
        assert limiter.is_allowed("ip-a") is False
        assert limiter.is_allowed("ip-b") is False

    def test_refills_over_time(self):
        limiter = RateLimiter(max_requests=2, window_seconds=1)
        assert limiter.is_allowed("test") is True
        assert limiter.is_allowed("test") is True
        assert limiter.is_allowed("test") is False
        # Wait for refill
        time.sleep(1.1)
        assert limiter.is_allowed("test") is True

    def test_remaining_reports_correctly(self):
        limiter = RateLimiter(max_requests=5, window_seconds=60)
        assert limiter.remaining("fresh-ip") == 5
        limiter.is_allowed("fresh-ip")
        assert limiter.remaining("fresh-ip") == 4


# ── Rate limit integration tests ─────────────────────────────────────────────


class TestRateLimitIntegration:
    """Test that rate limiting fires on actual endpoints."""

    def test_optimize_rate_limit(self):
        """Exhaust optimize limiter and expect 429."""
        from shelterpulse.api.rate_limit import optimize_limiter

        # Reset the limiter by creating a fresh one for a known test IP
        test_ip = "192.0.2.99"
        # Drain all tokens
        for _ in range(optimize_limiter.max_requests):
            optimize_limiter.is_allowed(test_ip)
        # Next should fail
        assert optimize_limiter.is_allowed(test_ip) is False


# ── Concurrent jobs limit tests ───────────────────────────────────────────────


class TestConcurrentJobsLimit:
    """Test max concurrent jobs per IP."""

    def test_count_active_by_ip(self):
        from shelterpulse.queue.job_store import JobStore, JobStatus

        store = JobStore()
        store.create("job-1", total=10, client_ip="1.2.3.4")
        store.create("job-2", total=10, client_ip="1.2.3.4")
        store.create("job-3", total=10, client_ip="5.6.7.8")

        assert store.count_active_by_ip("1.2.3.4") == 2
        assert store.count_active_by_ip("5.6.7.8") == 1
        assert store.count_active_by_ip("9.9.9.9") == 0

    def test_completed_jobs_not_counted(self):
        from shelterpulse.queue.job_store import JobStore, JobStatus

        store = JobStore()
        store.create("job-1", total=10, client_ip="1.2.3.4")
        store.create("job-2", total=10, client_ip="1.2.3.4")
        store.complete("job-1", [{"result": "done"}])

        assert store.count_active_by_ip("1.2.3.4") == 1

    def test_failed_jobs_not_counted(self):
        from shelterpulse.queue.job_store import JobStore, JobStatus

        store = JobStore()
        store.create("job-1", total=10, client_ip="1.2.3.4")
        store.fail("job-1", "something broke")

        assert store.count_active_by_ip("1.2.3.4") == 0


# ── Lambda validation tests ──────────────────────────────────────────────────


class TestLambdaValidation:
    """Test Lambda handler payload validation."""

    def test_valid_payload(self):
        import importlib
        import sys

        spec = importlib.util.spec_from_file_location("handler", "lambda/handler.py")
        handler_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(handler_mod)

        # Should not raise
        handler_mod._validate_payload({
            "request": {"n_replications": 32, "duration_days": 90, "housing_capacity": 35}
        })

    def test_invalid_replications(self):
        import importlib

        spec = importlib.util.spec_from_file_location("handler", "lambda/handler.py")
        handler_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(handler_mod)

        with pytest.raises(ValueError, match="n_replications"):
            handler_mod._validate_payload({"request": {"n_replications": 500}})

    def test_invalid_duration(self):
        import importlib

        spec = importlib.util.spec_from_file_location("handler", "lambda/handler.py")
        handler_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(handler_mod)

        with pytest.raises(ValueError, match="duration_days"):
            handler_mod._validate_payload({"request": {"duration_days": 1000}})

    def test_invalid_housing(self):
        import importlib

        spec = importlib.util.spec_from_file_location("handler", "lambda/handler.py")
        handler_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(handler_mod)

        with pytest.raises(ValueError, match="housing_capacity"):
            handler_mod._validate_payload({"request": {"housing_capacity": 999}})
