"""Queue abstraction: protocols for job dispatch and progress reporting.

Two implementations exist:
- sync_backend: in-process execution (default, preserves current behavior)
- rabbitmq_backend: publishes to RabbitMQ (local docker-compose)
- sqs_backend: publishes to AWS SQS (production)

Selected via QUEUE_BACKEND env var.
"""

from __future__ import annotations

from typing import Any, AsyncIterator, Protocol


class QueuePublisher(Protocol):
    """Publishes optimization jobs to a backend queue."""

    async def publish_job(self, job_id: str, payload: dict[str, Any]) -> None:
        """Dispatch a job for async processing.

        Args:
            job_id: Unique identifier for the job.
            payload: Serializable dict with scenario + optimization params.
        """
        ...

    async def close(self) -> None:
        """Release any connections held by the publisher."""
        ...


class ProgressListener(Protocol):
    """Listens for progress updates from workers."""

    async def listen(self, job_id: str) -> AsyncIterator[dict[str, Any]]:
        """Yield progress dicts as the worker reports them.

        Each dict has at minimum: {"done": int, "total": int}
        Final message has: {"status": "completed"|"failed", ...}
        """
        ...
        yield {}  # type: ignore[misc]
