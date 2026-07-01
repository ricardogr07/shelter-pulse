"""Queue abstraction layer.

Selects the queue backend based on the QUEUE_BACKEND environment variable:
- "sync" (default): in-process execution, no external dependencies
- "rabbitmq": publishes to RabbitMQ (local docker-compose development)
- "sqs": publishes to AWS SQS (production, Lambda consumer)
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from shelterpulse.queue.interface import ProgressListener, QueuePublisher


def get_publisher() -> "QueuePublisher":
    """Return the appropriate queue publisher based on QUEUE_BACKEND env var."""
    backend = os.getenv("QUEUE_BACKEND", "sync")

    if backend == "sqs":
        from shelterpulse.queue.sqs_backend import SQSPublisher

        return SQSPublisher()
    elif backend == "rabbitmq":
        from shelterpulse.queue.rabbitmq_backend import RabbitMQPublisher

        return RabbitMQPublisher()
    else:
        from shelterpulse.queue.sync_backend import SyncPublisher

        return SyncPublisher()


def get_progress_listener() -> "ProgressListener":
    """Return the appropriate progress listener based on QUEUE_BACKEND env var."""
    backend = os.getenv("QUEUE_BACKEND", "sync")

    if backend == "rabbitmq":
        from shelterpulse.queue.rabbitmq_backend import RabbitMQProgressListener

        return RabbitMQProgressListener()
    else:
        from shelterpulse.queue.sync_backend import SyncProgressListener

        return SyncProgressListener()
