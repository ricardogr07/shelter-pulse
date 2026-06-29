#!/bin/sh
# Consolidated entrypoint: FastAPI (uvicorn) behind nginx in one container.
# uvicorn binds localhost; nginx serves the static UI and proxies /api/* to it.
# ponytail: no supervisord. If nginx exits the container exits; uvicorn liveness
# is covered by the ECS Express /api/health check (a crash → task replaced).
# --root-path /api: the app is served behind nginx under /api, so FastAPI generates
# correct docs / openapi.json links (the prefix is stripped before it reaches uvicorn).
set -e

.venv/bin/uvicorn shelterpulse.api.app:app --host 127.0.0.1 --port 8000 --root-path /api &

exec nginx -g 'daemon off;'
