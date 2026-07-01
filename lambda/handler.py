"""AWS Lambda handler for SQS-triggered optimization jobs.

This handler is invoked by an SQS event source mapping. Each message contains
an optimization job payload. The handler runs the BO sweep and reports results
back to the API via the internal webhook.

Deployment: Container image (python:3.12-slim + shelterpulse-core).
Runtime: Lambda with VPC + EFS mount for DuckDB persistence.
"""

from __future__ import annotations

import json
import logging
import os
import urllib.request

logger = logging.getLogger()
logger.setLevel(logging.INFO)

API_URL = os.getenv("API_URL", "")
INTERNAL_KEY = os.getenv("INTERNAL_KEY", "")


def _post_json(url: str, data: dict) -> None:
    """POST JSON to the API webhook endpoint."""
    body = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Content-Type": "application/json",
            "X-Internal-Key": INTERNAL_KEY,
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:  # nosec B310
        resp.read()


def _validate_payload(payload: dict) -> None:
    """Validate payload bounds before running expensive computation."""
    req_data = payload.get("request", {})
    n_reps = req_data.get("n_replications", 32)
    duration = req_data.get("duration_days", 90)
    housing = req_data.get("housing_capacity", 35)

    if not (1 <= n_reps <= 128):
        raise ValueError(f"n_replications out of bounds: {n_reps}")
    if not (1 <= duration <= 365):
        raise ValueError(f"duration_days out of bounds: {duration}")
    if not (1 <= housing <= 500):
        raise ValueError(f"housing_capacity out of bounds: {housing}")


def _run_optimization(payload: dict) -> list[dict]:
    """Run the BO optimization sweep and return serialized results."""
    from shelterpulse.core.montecarlo import make_seed_set
    from shelterpulse.optimize.workflow import run_optimization_sweep
    from shelterpulse.api.app import _builder_to_scenario, _er_to_out, BuilderRequest

    req_data = payload.get("request", {})
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

    return [_er_to_out(r).model_dump() for r in results]


def handler(event: dict, context) -> dict:
    """Lambda entry point. Processes SQS messages containing optimization jobs.

    Args:
        event: SQS event with Records array.
        context: Lambda context (unused).

    Returns:
        Dict with statusCode and processed count.
    """
    records = event.get("Records", [])
    logger.info("Received %d SQS record(s)", len(records))

    processed = 0
    errors = 0

    for record in records:
        body = json.loads(record.get("body", "{}"))
        job_id = body.get("job_id", "unknown")
        job_type = body.get("type", "")

        logger.info("Processing job %s (type=%s)", job_id, job_type)

        try:
            if job_type == "optimize_builder":
                # Validate payload bounds
                _validate_payload(body)

                # Report progress start
                _post_json(
                    f"{API_URL}/internal/jobs/{job_id}/progress",
                    {"done": 0, "total": 15},
                )

                results = _run_optimization(body)

                # Report completion
                _post_json(
                    f"{API_URL}/internal/jobs/{job_id}/complete",
                    {"results": results},
                )
                logger.info("Job %s completed: %d results", job_id, len(results))
                processed += 1
            else:
                raise ValueError(f"Unknown job type: {job_type}")

        except Exception as e:
            logger.error("Job %s failed: %s", job_id, str(e), exc_info=True)
            try:
                _post_json(
                    f"{API_URL}/internal/jobs/{job_id}/fail",
                    {"error": str(e)},
                )
            except Exception:
                logger.error("Failed to report job failure for %s", job_id)
            errors += 1

    return {
        "statusCode": 200,
        "body": json.dumps({"processed": processed, "errors": errors}),
    }
