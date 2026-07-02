"""In-memory job store for tracking async optimization state.

Tracks job lifecycle: queued -> running -> completed/failed.
This will be backed by DuckDB in Phase 9 Track 3 (#44).
For now, in-memory dict is sufficient (single API process).

SSE pub/sub: subscribers register asyncio.Queue instances per job_id.
When progress/complete/fail is called, events are pushed to all subscribers.
"""

from __future__ import annotations

import asyncio
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class JobStatus(str, Enum):
    """Lifecycle states for an optimization job."""

    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Job:
    """State of a single optimization job."""

    job_id: str
    status: JobStatus = JobStatus.QUEUED
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    progress_done: int = 0
    progress_total: int = 0
    results: list[dict[str, Any]] = field(default_factory=list)
    error: str | None = None
    client_ip: str = ""


_JOB_TTL_SECONDS = 300  # 5 min: queued/running jobs older than this are presumed stuck
_JOB_RETENTION_SECONDS = 1800  # 30 min: completed/failed jobs older than this are purged


class JobStore:
    """Thread-safe in-memory job state store with async pub/sub for SSE.

    Single instance per API process. Jobs are kept in memory and lost on restart.
    This is acceptable for the hackathon scope - DuckDB persistence comes in #44.
    """

    def __init__(self) -> None:
        self._jobs: dict[str, Job] = {}
        self._lock = threading.Lock()
        self._subscribers: dict[str, list[tuple[asyncio.Queue, asyncio.AbstractEventLoop | None]]] = {}
        self._sub_lock = threading.Lock()

    def create(self, job_id: str, total: int = 0, client_ip: str = "") -> Job:
        """Register a new job as queued."""
        self.sweep_stale()
        job = Job(job_id=job_id, progress_total=total, client_ip=client_ip)
        with self._lock:
            self._jobs[job_id] = job
        return job

    def get(self, job_id: str) -> Job | None:
        """Get job by ID. Returns None if not found."""
        with self._lock:
            return self._jobs.get(job_id)

    def count_active_by_ip(self, client_ip: str) -> int:
        """Count jobs in queued/running state for a given client IP."""
        self.sweep_stale()
        with self._lock:
            return sum(
                1 for job in self._jobs.values()
                if job.client_ip == client_ip
                and job.status in (JobStatus.QUEUED, JobStatus.RUNNING)
            )

    def sweep_stale(self, ttl_seconds: int = _JOB_TTL_SECONDS) -> int:
        """Fail queued/running jobs that haven't been updated within ttl_seconds.

        Guards against jobs stuck forever when a worker's webhook callback never
        arrives (wrong URL, auth mismatch, crash). Also purges old completed/failed
        jobs so the in-memory dict doesn't grow unbounded. Safe to call frequently -
        it's called lazily from create() and count_active_by_ip() rather than on a
        background timer.
        """
        now = datetime.now(timezone.utc)
        timed_out: list[str] = []
        with self._lock:
            for job in self._jobs.values():
                if job.status in (JobStatus.QUEUED, JobStatus.RUNNING):
                    if (now - job.updated_at).total_seconds() > ttl_seconds:
                        job.status = JobStatus.FAILED
                        job.error = "Job timed out"
                        job.updated_at = now
                        timed_out.append(job.job_id)
            stale_ids = [
                job_id for job_id, job in self._jobs.items()
                if job.status in (JobStatus.COMPLETED, JobStatus.FAILED)
                and (now - job.updated_at).total_seconds() > _JOB_RETENTION_SECONDS
            ]
            for job_id in stale_ids:
                del self._jobs[job_id]

        for job_id in timed_out:
            self._notify(job_id, {"event": "error", "message": "Job timed out"})

        return len(timed_out)

    def update_progress(self, job_id: str, done: int, total: int) -> None:
        """Update progress counters for a running job."""
        with self._lock:
            job = self._jobs.get(job_id)
            if job:
                job.status = JobStatus.RUNNING
                job.progress_done = done
                job.progress_total = total
                job.updated_at = datetime.now(timezone.utc)
        self._notify(job_id, {"event": "progress", "done": done, "total": total})

    def complete(self, job_id: str, results: list[dict[str, Any]]) -> None:
        """Mark job as completed with results."""
        with self._lock:
            job = self._jobs.get(job_id)
            if job:
                job.status = JobStatus.COMPLETED
                job.results = results
                job.updated_at = datetime.now(timezone.utc)
        self._notify(job_id, {"event": "complete", "results": results})

    def fail(self, job_id: str, error: str) -> None:
        """Mark job as failed with error message."""
        with self._lock:
            job = self._jobs.get(job_id)
            if job:
                job.status = JobStatus.FAILED
                job.error = error
                job.updated_at = datetime.now(timezone.utc)
        self._notify(job_id, {"event": "error", "message": error})

    # ── Pub/sub for SSE ───────────────────────────────────────────────────────

    def subscribe(self, job_id: str) -> asyncio.Queue:
        """Register a subscriber queue for SSE events on a job.

        Captures the current running event loop so notifications from sync
        threads can be marshalled via call_soon_threadsafe.
        If no loop is running (e.g. tests), notifications use direct put_nowait.
        """
        queue: asyncio.Queue = asyncio.Queue()
        try:
            loop: asyncio.AbstractEventLoop | None = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        with self._sub_lock:
            if job_id not in self._subscribers:
                self._subscribers[job_id] = []
            self._subscribers[job_id].append((queue, loop))
        return queue

    def unsubscribe(self, job_id: str, queue: asyncio.Queue) -> None:
        """Remove a subscriber queue."""
        with self._sub_lock:
            if job_id in self._subscribers:
                self._subscribers[job_id] = [
                    (q, loop) for q, loop in self._subscribers[job_id] if q is not queue
                ]
                if not self._subscribers[job_id]:
                    del self._subscribers[job_id]

    def _notify(self, job_id: str, event: dict[str, Any]) -> None:
        """Push an event to all subscribers for a job.

        Uses call_soon_threadsafe to marshal notifications from sync webhook
        threads onto the subscriber's event loop, ensuring the awaiting
        queue.get() is properly woken.

        If the subscriber was created without a running loop (tests),
        falls back to direct put_nowait.
        """
        with self._sub_lock:
            subscribers = list(self._subscribers.get(job_id, []))
        if not subscribers:
            return
        for queue, loop in subscribers:
            if loop is not None and loop.is_running():
                loop.call_soon_threadsafe(queue.put_nowait, event)
            else:
                # No running loop (tests, sync context) - push directly
                queue.put_nowait(event)


# Singleton instance for the API process
job_store = JobStore()
