"""In-memory job store for tracking async optimization state.

Tracks job lifecycle: queued -> running -> completed/failed.
This will be backed by DuckDB in Phase 9 Track 3 (#44).
For now, in-memory dict is sufficient (single API process).
"""

from __future__ import annotations

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


class JobStore:
    """Thread-safe in-memory job state store.

    Single instance per API process. Jobs are kept in memory and lost on restart.
    This is acceptable for the hackathon scope - DuckDB persistence comes in #44.
    """

    def __init__(self) -> None:
        self._jobs: dict[str, Job] = {}
        self._lock = threading.Lock()

    def create(self, job_id: str, total: int = 0) -> Job:
        """Register a new job as queued."""
        job = Job(job_id=job_id, progress_total=total)
        with self._lock:
            self._jobs[job_id] = job
        return job

    def get(self, job_id: str) -> Job | None:
        """Get job by ID. Returns None if not found."""
        with self._lock:
            return self._jobs.get(job_id)

    def update_progress(self, job_id: str, done: int, total: int) -> None:
        """Update progress counters for a running job."""
        with self._lock:
            job = self._jobs.get(job_id)
            if job:
                job.status = JobStatus.RUNNING
                job.progress_done = done
                job.progress_total = total
                job.updated_at = datetime.now(timezone.utc)

    def complete(self, job_id: str, results: list[dict[str, Any]]) -> None:
        """Mark job as completed with results."""
        with self._lock:
            job = self._jobs.get(job_id)
            if job:
                job.status = JobStatus.COMPLETED
                job.results = results
                job.updated_at = datetime.now(timezone.utc)

    def fail(self, job_id: str, error: str) -> None:
        """Mark job as failed with error message."""
        with self._lock:
            job = self._jobs.get(job_id)
            if job:
                job.status = JobStatus.FAILED
                job.error = error
                job.updated_at = datetime.now(timezone.utc)


# Singleton instance for the API process
job_store = JobStore()
