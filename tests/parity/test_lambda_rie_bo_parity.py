"""Parity test: the built Lambda worker image actually runs real BO.

Regression guard for the pyDOE-shim bug (fixed in PR #114): the Dockerfile
silently fell back to random search in every deployed environment because a
compat shim was written to the wrong site-packages directory. That bug
produced no test failure anywhere - only a live CloudWatch log line proved
it. This test builds the real images and dispatches a real optimize_builder
job through the AWS Lambda Runtime Interface Emulator, so a similar
regression fails here instead of shipping silently again.

Slow (image build + a real BO sweep). Not part of the default `tox -e test`
or `tox -e e2e` gates. Run explicitly:

    docker --version  # requires Docker
    uv run pytest tests/parity/ -v -s
"""

from __future__ import annotations

import json
import shutil
import subprocess
import time

import pytest

REPO_ROOT = __file__.rsplit("tests", 1)[0].rstrip("/\\")
WORKER_IMAGE = "shelterpulse-worker-parity-test"
RIE_IMAGE = "shelterpulse-worker-rie-parity-test"
CONTAINER_NAME = "shelterpulse-rie-parity-test"
RIE_PORT = 9123

pytestmark = pytest.mark.skipif(
    shutil.which("docker") is None,
    reason="docker not available",
)


def _run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True, **kwargs)


@pytest.fixture(scope="module")
def rie_container():
    build = _run(["docker", "build", "-f", "lambda/Dockerfile", "-t", WORKER_IMAGE, "."])
    assert build.returncode == 0, f"worker image build failed:\n{build.stderr}"

    # docker/lambda-rie.Dockerfile hardcodes FROM shelterpulse-worker-local;
    # tag our freshly built image under that name so the build uses it.
    tag = _run(["docker", "tag", WORKER_IMAGE, "shelterpulse-worker-local"])
    assert tag.returncode == 0, f"docker tag failed:\n{tag.stderr}"

    build_rie = _run(["docker", "build", "-f", "docker/lambda-rie.Dockerfile", "-t", RIE_IMAGE, "."])
    assert build_rie.returncode == 0, f"RIE image build failed:\n{build_rie.stderr}"

    _run(["docker", "rm", "-f", CONTAINER_NAME])
    run = _run([
        "docker", "run", "-d", "--name", CONTAINER_NAME,
        "-p", f"{RIE_PORT}:8080",
        "-e", "API_URL=http://127.0.0.1:1/api",
        "-e", "INTERNAL_KEY=parity-test",
        RIE_IMAGE,
    ])
    assert run.returncode == 0, f"container start failed:\n{run.stderr}"
    time.sleep(2)

    yield CONTAINER_NAME

    _run(["docker", "rm", "-f", CONTAINER_NAME])


def test_real_bo_runs_in_built_lambda_image(rie_container):
    """Dispatch a real optimize_builder job and confirm GP+EI actually ran."""
    event = {
        "Records": [{
            "body": json.dumps({
                "job_id": "parity-test-job",
                "type": "optimize_builder",
                "request": {"duration_days": 30, "n_replications": 4},
                "consent_storage": False,
                "is_test_data": True,
            })
        }]
    }
    invoke = _run([
        "curl", "-sS", "-X", "POST",
        f"http://localhost:{RIE_PORT}/2015-03-31/functions/function/invocations",
        "-d", json.dumps(event),
    ], timeout=120)
    assert invoke.returncode == 0, invoke.stderr

    logs = _run(["docker", "logs", rie_container]).stdout

    assert "jax/jaxbo import succeeded" in logs, (
        "jax/jaxbo failed to import in the built image (pyDOE-shim-style "
        f"regression). Full logs:\n{logs}"
    )
    assert "optimize_jaxbo: using GP+EI" in logs, (
        f"optimizer used random-search fallback, not real BO. Full logs:\n{logs}"
    )
