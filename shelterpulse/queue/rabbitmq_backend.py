"""RabbitMQ queue backend.

Publishes optimization jobs to a RabbitMQ exchange.
Worker containers consume from the queue and run the BO sweep.

Requires: aio-pika (install with `uv sync --extra worker`)
"""

from __future__ import annotations

import json
import os
from typing import Any, AsyncIterator


class RabbitMQPublisher:
    """Publishes optimization jobs to RabbitMQ."""

    def __init__(self) -> None:
        self._url = os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672/")
        self._connection = None

    async def publish_job(self, job_id: str, payload: dict[str, Any]) -> None:
        """Publish job to RabbitMQ optimization exchange."""
        try:
            import aio_pika  # type: ignore[import-untyped]
        except ImportError as e:
            raise ImportError("aio-pika required: install with `uv sync --extra worker`") from e

        if not self._connection:
            self._connection = await aio_pika.connect_robust(self._url)
        channel = await self._connection.channel()
        exchange = await channel.declare_exchange(
            "optimization", aio_pika.ExchangeType.DIRECT, durable=True
        )
        await exchange.publish(
            aio_pika.Message(
                body=json.dumps({"job_id": job_id, **payload}).encode(),
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            ),
            routing_key="jobs",
        )

    async def close(self) -> None:
        """Close the RabbitMQ connection."""
        if self._connection:
            await self._connection.close()
            self._connection = None


class RabbitMQProgressListener:
    """Consumes progress messages from RabbitMQ progress queue."""

    def __init__(self) -> None:
        self._url = os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672/")

    async def listen(self, job_id: str) -> AsyncIterator[dict[str, Any]]:
        """Yield progress updates for a specific job from RabbitMQ."""
        try:
            import aio_pika  # type: ignore[import-untyped]
        except ImportError as e:
            raise ImportError("aio-pika required: install with `uv sync --extra worker`") from e

        connection = await aio_pika.connect_robust(self._url)
        try:
            channel = await connection.channel()
            queue = await channel.declare_queue(
                f"progress.{job_id}", durable=False, auto_delete=True
            )
            async with queue.iterator() as messages:
                async for msg in messages:
                    data = json.loads(msg.body)
                    await msg.ack()
                    yield data
                    if data.get("status") in ("completed", "failed"):
                        break
        finally:
            await connection.close()
