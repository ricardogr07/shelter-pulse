"""Synchronous (in-process) queue backend.

This is the default backend. It runs the optimization sweep directly in the
API process, preserving the exact behavior from before the queue abstraction
was introduced. No external services required.

Use this when QUEUE_BACKEND=sync (the default).
"""

from __future__ import annotations

from typing import Any, AsyncIterator


class SyncPublisher:
    """Executes jobs in-process. No actual queue involved."""

    async def publish_job(self, job_id: str, payload: dict[str, Any]) -> None:
        """Run the optimization sweep synchronously and store results.

        In sync mode the API blocks until the sweep completes,
        so this is a no-op placeholder. The actual execution happens
        in the endpoint handler which calls run_optimization_sweep directly.
        """
        # In sync mode, the endpoint itself calls run_optimization_sweep()
        # and returns results directly. This publish is intentionally a no-op.
        pass

    async def close(self) -> None:
        """No resources to release in sync mode."""
        pass


class SyncProgressListener:
    """No-op progress listener for sync mode.

    In sync mode, results are returned directly in the HTTP response,
    so there is no progress streaming.
    """

    async def listen(self, job_id: str) -> AsyncIterator[dict[str, Any]]:
        """Yields nothing - sync mode has no streaming progress."""
        return
        yield  # make this a generator  # noqa: RET503
