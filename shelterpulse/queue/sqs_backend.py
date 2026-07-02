"""AWS SQS queue backend.

Publishes optimization jobs to an SQS FIFO queue.
Lambda consumes from the queue and runs the BO sweep.

Requires: boto3 (install with `uv sync --extra aws`)
"""

from __future__ import annotations

import json
import os
from typing import Any


class SQSPublisher:
    """Publishes optimization jobs to AWS SQS."""

    def __init__(self) -> None:
        try:
            import boto3  # type: ignore[import-untyped]
        except ImportError as e:
            raise ImportError("boto3 required: install with `uv sync --extra aws`") from e

        self._sqs = boto3.client("sqs")
        self._queue_url = os.getenv("SQS_QUEUE_URL", "")

    async def publish_job(self, job_id: str, payload: dict[str, Any]) -> None:
        """Send job to SQS FIFO queue."""
        self._sqs.send_message(
            QueueUrl=self._queue_url,
            MessageBody=json.dumps({"job_id": job_id, **payload}),
            MessageGroupId="optimization",
            MessageDeduplicationId=job_id,
        )

    async def close(self) -> None:
        """No persistent connection to close for SQS."""
        pass
