"""Tests for the queue abstraction layer."""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from shelterpulse.queue import get_publisher, get_progress_listener
from shelterpulse.queue.interface import QueuePublisher, ProgressListener
from shelterpulse.queue.sync_backend import SyncPublisher, SyncProgressListener


class TestFactory:
    """Test that the factory returns the correct backend based on env var."""

    def test_default_returns_sync_publisher(self):
        """With no env var set, factory returns SyncPublisher."""
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("QUEUE_BACKEND", None)
            publisher = get_publisher()
            assert isinstance(publisher, SyncPublisher)

    def test_sync_explicitly_returns_sync_publisher(self):
        """QUEUE_BACKEND=sync returns SyncPublisher."""
        with patch.dict(os.environ, {"QUEUE_BACKEND": "sync"}):
            publisher = get_publisher()
            assert isinstance(publisher, SyncPublisher)

    def test_backend_env_ignored_returns_sync(self):
        """The async backends are removed: any QUEUE_BACKEND value returns sync."""
        with patch.dict(os.environ, {"QUEUE_BACKEND": "rabbitmq"}):
            assert isinstance(get_publisher(), SyncPublisher)

    def test_default_returns_sync_progress_listener(self):
        """Default progress listener is SyncProgressListener."""
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("QUEUE_BACKEND", None)
            listener = get_progress_listener()
            assert isinstance(listener, SyncProgressListener)


class TestSyncPublisher:
    """Test the synchronous (in-process) publisher."""

    @pytest.mark.asyncio
    async def test_publish_job_is_noop(self):
        """SyncPublisher.publish_job does nothing (sweep runs in endpoint)."""
        publisher = SyncPublisher()
        # Should not raise
        await publisher.publish_job("test-job-123", {"scenario": "test"})

    @pytest.mark.asyncio
    async def test_close_is_noop(self):
        """SyncPublisher.close does nothing."""
        publisher = SyncPublisher()
        await publisher.close()

    @pytest.mark.asyncio
    async def test_publish_job_accepts_any_payload(self):
        """SyncPublisher accepts arbitrary payload dicts without error."""
        publisher = SyncPublisher()
        await publisher.publish_job("job-1", {})
        await publisher.publish_job("job-2", {"key": "value", "nested": {"a": 1}})
        await publisher.publish_job("job-3", {"list": [1, 2, 3]})


class TestSyncProgressListener:
    """Test the synchronous progress listener."""

    @pytest.mark.asyncio
    async def test_listen_yields_nothing(self):
        """SyncProgressListener.listen is an empty async generator."""
        listener = SyncProgressListener()
        results = []
        async for msg in listener.listen("job-123"):
            results.append(msg)
        assert results == []


class TestProtocolCompliance:
    """Verify that concrete classes satisfy the Protocol contracts."""

    def test_sync_publisher_satisfies_protocol(self):
        """SyncPublisher has all methods required by QueuePublisher."""
        publisher = SyncPublisher()
        assert hasattr(publisher, "publish_job")
        assert hasattr(publisher, "close")
        assert callable(publisher.publish_job)
        assert callable(publisher.close)

    def test_sync_listener_satisfies_protocol(self):
        """SyncProgressListener has all methods required by ProgressListener."""
        listener = SyncProgressListener()
        assert hasattr(listener, "listen")
        assert callable(listener.listen)
