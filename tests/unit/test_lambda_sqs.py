"""Tests for Lambda handler and SQS backend."""

from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# lambda/ is a reserved keyword in Python so we can't do `from lambda.handler import ...`
# We import it using importlib instead.
_lambda_dir = str(Path(__file__).parent.parent.parent / "lambda")
if _lambda_dir not in sys.path:
    sys.path.insert(0, _lambda_dir)


def _import_handler():
    """Import handler module from the lambda/ directory."""
    spec = importlib.util.spec_from_file_location(
        "lambda_handler",
        Path(__file__).parent.parent.parent / "lambda" / "handler.py",
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestLambdaHandler:
    """Test the Lambda SQS event handler."""

    def test_handler_processes_single_record(self):
        """Handler processes one SQS record and calls webhook."""
        mod = _import_handler()

        mock_results = [{"mean_overflow_cat_days": 10.0, "foster_support": 0.5}]

        event = {
            "Records": [{
                "body": json.dumps({
                    "job_id": "test-job-1",
                    "type": "optimize_builder",
                    "request": {
                        "duration_days": 30,
                        "housing_capacity": 20,
                        "n_replications": 4,
                    },
                })
            }]
        }

        with patch.object(mod, "_run_optimization", return_value=mock_results), \
             patch.object(mod, "_post_json") as mock_post:
            result = mod.handler(event, None)

        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert body["processed"] == 1
        assert body["errors"] == 0
        # Only complete webhook called (progress is reported via on_progress
        # callback which doesn't fire when _run_optimization is mocked)
        assert mock_post.call_count == 1
        call_url = mock_post.call_args_list[0][0][0]
        assert "/internal/jobs/test-job-1/complete" in call_url

    def test_handler_reports_failure_on_error(self):
        """Handler calls fail webhook when optimization raises."""
        mod = _import_handler()

        event = {
            "Records": [{
                "body": json.dumps({
                    "job_id": "test-job-fail",
                    "type": "optimize_builder",
                    "request": {},
                })
            }]
        }

        with patch.object(mod, "_run_optimization", side_effect=ValueError("bad input")), \
             patch.object(mod, "_post_json") as mock_post:
            result = mod.handler(event, None)

        body = json.loads(result["body"])
        assert body["errors"] == 1
        assert body["processed"] == 0

    def test_handler_handles_unknown_job_type(self):
        """Handler fails gracefully for unknown job types."""
        mod = _import_handler()

        event = {
            "Records": [{
                "body": json.dumps({
                    "job_id": "test-job-unknown",
                    "type": "invalid_type",
                    "request": {},
                })
            }]
        }

        with patch.object(mod, "_post_json"):
            result = mod.handler(event, None)

        body = json.loads(result["body"])
        assert body["errors"] == 1

    def test_handler_processes_empty_records(self):
        """Handler handles empty Records array gracefully."""
        mod = _import_handler()

        with patch.object(mod, "_post_json"):
            result = mod.handler({"Records": []}, None)

        body = json.loads(result["body"])
        assert body["processed"] == 0
        assert body["errors"] == 0


class TestSQSBackend:
    """Test the SQS publisher (mocked boto3)."""

    def test_sqs_publisher_interface_exists(self):
        """SQSPublisher class exists and has the right methods."""
        from shelterpulse.queue.sqs_backend import SQSPublisher
        assert hasattr(SQSPublisher, "publish_job")
        assert hasattr(SQSPublisher, "close")

    def test_sqs_publisher_requires_boto3(self):
        """SQSPublisher raises ImportError if boto3 is not installed."""
        with patch.dict(sys.modules, {"boto3": None}):
            # Force reimport
            import shelterpulse.queue.sqs_backend as sqs_mod
            importlib.reload(sqs_mod)
            with pytest.raises(ImportError, match="boto3 required"):
                sqs_mod.SQSPublisher()
