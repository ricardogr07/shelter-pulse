"""Tests for SSE progress streaming and optimization progress callback."""

import asyncio
import json
import threading

import pytest
from fastapi.testclient import TestClient

from shelterpulse.api.app import app
from shelterpulse.queue.job_store import JobStatus, JobStore, job_store


client = TestClient(app)


# ── Progress callback tests ───────────────────────────────────────────────────


class TestProgressCallback:
    """Test that optimization functions call on_progress correctly."""

    def test_inprocess_sweep_calls_callback(self):
        """_inprocess_sweep reports progress for baselines + candidates."""
        from shelterpulse.core.montecarlo import make_seed_set
        from shelterpulse.core.schema import load_scenario
        from shelterpulse.optimize.workflow import _inprocess_sweep
        from pathlib import Path

        scenario_path = Path(__file__).parent.parent.parent / "scenarios" / "whisker_haven.yaml"
        scenario = load_scenario(scenario_path)
        seeds = make_seed_set(scenario.seed, 4)

        progress_calls: list[tuple[int, int]] = []

        def on_progress(done: int, total: int) -> None:
            progress_calls.append((done, total))

        results = _inprocess_sweep(scenario, 5000, 3, seeds, on_progress=on_progress)

        # 5 baselines + 3 random = 8 calls
        assert len(progress_calls) == 8
        # All have same total
        assert all(t == 8 for _, t in progress_calls)
        # Done increments from 1 to 8
        assert [d for d, _ in progress_calls] == list(range(1, 9))
        # Results include all evaluated candidates
        assert len(results) == 8

    def test_run_optimization_sweep_passes_callback(self):
        """run_optimization_sweep propagates on_progress to sub-functions."""
        from shelterpulse.core.montecarlo import make_seed_set
        from shelterpulse.core.schema import load_scenario
        from shelterpulse.optimize.workflow import run_optimization_sweep
        from pathlib import Path

        scenario_path = Path(__file__).parent.parent.parent / "scenarios" / "whisker_haven.yaml"
        scenario = load_scenario(scenario_path)
        seeds = make_seed_set(scenario.seed, 4)

        progress_calls: list[tuple[int, int]] = []

        def on_progress(done: int, total: int) -> None:
            progress_calls.append((done, total))

        results = run_optimization_sweep(
            scenario, budget=5000, n_candidates=5, seed_set=seeds,
            use_bo=True, on_progress=on_progress,
        )

        # Should have been called at least once
        assert len(progress_calls) > 0
        # Last done should equal total for the BO candidates
        # (baselines report separately)
        assert results  # non-empty

    def test_none_callback_is_safe(self):
        """Passing on_progress=None does not crash."""
        from shelterpulse.core.montecarlo import make_seed_set
        from shelterpulse.core.schema import load_scenario
        from shelterpulse.optimize.workflow import run_optimization_sweep
        from pathlib import Path

        scenario_path = Path(__file__).parent.parent.parent / "scenarios" / "whisker_haven.yaml"
        scenario = load_scenario(scenario_path)
        seeds = make_seed_set(scenario.seed, 4)

        # Should not raise
        results = run_optimization_sweep(
            scenario, budget=5000, n_candidates=3, seed_set=seeds,
            use_bo=True, on_progress=None,
        )
        assert len(results) > 0


# ── Job store pub/sub tests ───────────────────────────────────────────────────


class TestJobStorePubSub:
    """Test the asyncio pub/sub mechanism in JobStore."""

    def test_subscribe_and_notify_progress(self):
        """Subscriber receives progress events."""
        store = JobStore()
        store.create("job-sub-1", total=10)
        queue = store.subscribe("job-sub-1")

        store.update_progress("job-sub-1", 3, 10)

        # Should have one event in the queue
        assert not queue.empty()
        event = queue.get_nowait()
        assert event["event"] == "progress"
        assert event["done"] == 3
        assert event["total"] == 10

    def test_subscribe_and_notify_complete(self):
        """Subscriber receives complete event."""
        store = JobStore()
        store.create("job-sub-2", total=5)
        queue = store.subscribe("job-sub-2")

        store.complete("job-sub-2", [{"result": "data"}])

        event = queue.get_nowait()
        assert event["event"] == "complete"
        assert event["results"] == [{"result": "data"}]

    def test_subscribe_and_notify_fail(self):
        """Subscriber receives error event."""
        store = JobStore()
        store.create("job-sub-3", total=5)
        queue = store.subscribe("job-sub-3")

        store.fail("job-sub-3", "something broke")

        event = queue.get_nowait()
        assert event["event"] == "error"
        assert event["message"] == "something broke"

    def test_unsubscribe_removes_queue(self):
        """After unsubscribe, no more events are delivered."""
        store = JobStore()
        store.create("job-sub-4", total=5)
        queue = store.subscribe("job-sub-4")
        store.unsubscribe("job-sub-4", queue)

        store.update_progress("job-sub-4", 1, 5)

        assert queue.empty()

    def test_multiple_subscribers(self):
        """Multiple subscribers each get their own copy of events."""
        store = JobStore()
        store.create("job-sub-5", total=5)
        q1 = store.subscribe("job-sub-5")
        q2 = store.subscribe("job-sub-5")

        store.update_progress("job-sub-5", 2, 5)

        e1 = q1.get_nowait()
        e2 = q2.get_nowait()
        assert e1 == e2 == {"event": "progress", "done": 2, "total": 5}


# ── SSE endpoint tests ────────────────────────────────────────────────────────


class TestSSEEndpoint:
    """Test the SSE streaming endpoint."""

    def test_stream_404_for_unknown_job(self):
        """GET /optimize/{job_id}/stream returns 404 for unknown job."""
        resp = client.get("/optimize/nonexistent-id/stream")
        assert resp.status_code == 404

    def test_stream_emits_current_state_if_completed(self):
        """If job already completed, stream immediately emits complete event."""
        job_id = "sse-test-completed"
        job_store.create(job_id, total=5)
        job_store.complete(job_id, [{"overflow": 10.5}])

        with client.stream("GET", f"/optimize/{job_id}/stream") as resp:
            assert resp.status_code == 200
            assert resp.headers["content-type"] == "text/event-stream; charset=utf-8"

            lines = []
            for line in resp.iter_lines():
                lines.append(line)
                # SSE events end with empty line; stop after seeing data for complete
                if line.startswith("data:") and "overflow" in line:
                    break

            full = "\n".join(lines)
            assert "event: complete" in full
            assert "overflow" in full

    def test_stream_emits_current_state_if_failed(self):
        """If job already failed, stream immediately emits error event."""
        job_id = "sse-test-failed"
        job_store.create(job_id, total=5)
        job_store.fail(job_id, "boom")

        with client.stream("GET", f"/optimize/{job_id}/stream") as resp:
            assert resp.status_code == 200

            lines = []
            for line in resp.iter_lines():
                lines.append(line)
                if line.startswith("data:") and "boom" in line:
                    break

            full = "\n".join(lines)
            assert "event: error" in full
            assert "boom" in full

    def test_stream_progress_then_complete(self):
        """Stream receives progress events then complete."""
        job_id = "sse-test-live"
        job_store.create(job_id, total=3)

        def _simulate_worker():
            """Simulate worker reporting progress in a separate thread."""
            import time
            time.sleep(0.2)
            job_store.update_progress(job_id, 1, 3)
            time.sleep(0.1)
            job_store.update_progress(job_id, 2, 3)
            time.sleep(0.1)
            job_store.update_progress(job_id, 3, 3)
            time.sleep(0.1)
            job_store.complete(job_id, [{"result": "final"}])

        worker = threading.Thread(target=_simulate_worker)
        worker.start()

        events_seen = []
        with client.stream("GET", f"/optimize/{job_id}/stream") as resp:
            assert resp.status_code == 200
            for line in resp.iter_lines():
                if line.startswith("event: "):
                    events_seen.append(line.replace("event: ", ""))
                if line.startswith("data:") and "final" in line:
                    break

        worker.join(timeout=5)

        assert "progress" in events_seen
        assert "complete" in events_seen


# ── Lambda validation tests (from previous PR but extended) ───────────────────


class TestLambdaProgressReporting:
    """Test Lambda handler progress reporting pattern."""

    def test_progress_reporter_closure(self):
        """The _report_progress closure pattern works correctly."""
        import importlib.util

        spec = importlib.util.spec_from_file_location("handler", "lambda/handler.py")
        handler_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(handler_mod)

        # Verify _run_optimization accepts on_progress parameter
        import inspect
        sig = inspect.signature(handler_mod._run_optimization)
        assert "on_progress" in sig.parameters
