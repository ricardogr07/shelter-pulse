"""Queue abstraction layer.

Only the synchronous (in-process) backend remains. The async RabbitMQ/SQS
backends were removed when ShelterPulse became a static showcase with no
deployed backend. These functions keep their signatures so the API layer is
unchanged; they always return the sync implementation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from shelterpulse.queue.interface import ProgressListener, QueuePublisher


def get_publisher() -> "QueuePublisher":
    """Return the synchronous, in-process queue publisher."""
    from shelterpulse.queue.sync_backend import SyncPublisher

    return SyncPublisher()


def get_progress_listener() -> "ProgressListener":
    """Return the synchronous progress listener."""
    from shelterpulse.queue.sync_backend import SyncProgressListener

    return SyncProgressListener()
