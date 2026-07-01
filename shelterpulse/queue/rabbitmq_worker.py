"""RabbitMQ worker: consumes optimization jobs and reports results via webhook.

Run as: python -m shelterpulse.queue.rabbitmq_worker

Connects to RabbitMQ, consumes from the 'optimization' exchange with routing key
'jobs', runs the BO sweep, and POSTs results back to the API via the internal
webhook endpoints.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
import urllib.request

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [worker] %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)

RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://shelter:pulse@localhost:5672/")
API_URL = os.getenv("API_URL", "http://localhost:8000")
INTERNAL_KEY = os.getenv("INTERNAL_KEY", "dev-key-123")
QUEUE_NAME = "optimization_jobs"


def _post_json(url: str, data: dict) -> None:
    """POST JSON to a URL using stdlib (no httpx dependency needed)."""
    body = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Content-Type": "application/json",
            "X-Internal-Key": INTERNAL_KEY,
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:  # nosec B310
            resp.read()
    except Exception as e:
        logger.warning("Webhook POST to %s failed: %s", url, e)


async def _process_job(body: bytes) -> None:
    """Process a single optimization job message."""
    payload = json.loads(body)
    job_id = payload.get("job_id", "unknown")
    job_type = payload.get("type", "")
    logger.info("Processing job %s (type=%s)", job_id, job_type)

    try:
        if job_type == "optimize_builder":
            results = _run_optimization(payload)

            # Report completion
            _post_json(
                f"{API_URL}/internal/jobs/{job_id}/complete",
                {"results": results},
            )
            logger.info("Job %s completed: %d results", job_id, len(results))
        else:
            raise ValueError(f"Unknown job type: {job_type}")

    except Exception as e:
        logger.error("Job %s failed: %s", job_id, str(e))
        _post_json(
            f"{API_URL}/internal/jobs/{job_id}/fail",
            {"error": str(e)},
        )


def _run_optimization(payload: dict) -> list[dict]:
    """Run the BO optimization sweep and return serialized results."""
    from shelterpulse.core.montecarlo import make_seed_set
    from shelterpulse.optimize.workflow import run_optimization_sweep

    # Import here to defer heavy imports until actually processing
    req_data = payload.get("request", {})

    # Build scenario from request data (same logic as API)
    from shelterpulse.api.app import _builder_to_scenario, _er_to_out, BuilderRequest

    req = BuilderRequest.model_validate(req_data)
    scenario = _builder_to_scenario(req)
    seeds = make_seed_set(scenario.seed, req.n_replications)

    results = run_optimization_sweep(
        scenario,
        budget=req.intervention_budget,
        n_candidates=15,
        seed_set=seeds,
        use_bo=True,
    )

    # Serialize to dicts (JSON-compatible)
    return [_er_to_out(r).model_dump() for r in results]


async def _run_worker() -> None:
    """Main worker loop: connect to RabbitMQ and consume forever."""
    try:
        import aio_pika  # type: ignore[import-untyped]
    except ImportError:
        logger.error("aio-pika not installed. Run: uv sync --extra worker")
        sys.exit(1)

    logger.info("Connecting to RabbitMQ at %s", RABBITMQ_URL)

    # Retry connection with backoff
    connection = None
    for attempt in range(10):
        try:
            connection = await aio_pika.connect_robust(RABBITMQ_URL)
            break
        except Exception as e:
            wait = min(2**attempt, 30)
            logger.warning("RabbitMQ not ready (attempt %d): %s. Retrying in %ds...", attempt + 1, e, wait)
            await asyncio.sleep(wait)

    if not connection:
        logger.error("Could not connect to RabbitMQ after 10 attempts. Exiting.")
        sys.exit(1)

    logger.info("Connected to RabbitMQ. Starting consumer...")

    channel = await connection.channel()
    await channel.set_qos(prefetch_count=1)

    # Declare exchange and queue
    exchange = await channel.declare_exchange(
        "optimization", aio_pika.ExchangeType.DIRECT, durable=True
    )
    queue = await channel.declare_queue(QUEUE_NAME, durable=True)
    await queue.bind(exchange, routing_key="jobs")

    logger.info("Listening on queue '%s'...", QUEUE_NAME)

    async with queue.iterator() as messages:
        async for message in messages:
            async with message.process():
                try:
                    await _process_job(message.body)
                except Exception as e:
                    logger.error("Unhandled error processing message: %s", e)


def main() -> None:
    """Entry point for the worker process."""
    logger.info("ShelterPulse RabbitMQ Worker starting...")
    asyncio.run(_run_worker())


if __name__ == "__main__":
    main()
