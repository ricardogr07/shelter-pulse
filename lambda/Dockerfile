# Lambda worker image: lean build with only shelterpulse-core dependencies.
# No FastAPI, no nginx, no uvicorn - just the optimization engine.
#
# Build: docker build -f lambda/Dockerfile -t shelterpulse-worker .
# Test locally: docker run -p 9000:8080 shelterpulse-worker
#   curl -X POST "http://localhost:9000/2015-03-31/functions/function/invocations" -d '...'

FROM python:3.12-slim

# Install uv for fast dependency resolution
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install only optimize deps (core simulation + BO engine) - no API/CLI deps
RUN uv sync --no-dev --no-install-project --extra optimize

# pyDOE shim (same as main Dockerfile)
RUN python -c "import site; sp=[p for p in site.getsitepackages() if 'site-packages' in p][0]; open(sp+'/pyDOE.py','w').write('from pydoe import *\nfrom pydoe import lhs\n')"

# Fix jaxbo compat with JAX 0.10+
RUN find /app/.venv -path '*/jaxbo/*.py' \
    -exec sed -i 's/np\.clip(\([^,]*\),\s*a_min=\([^,)]*\))/np.clip(\1, \2, None)/g' {} \;

# Install Lambda runtime interface client
RUN .venv/bin/pip install awslambdaric

# Copy application source
COPY shelterpulse/ shelterpulse/
COPY scenarios/ scenarios/
COPY lambda/handler.py ./

ENV PYTHONPATH=/app

# Lambda runtime interface
ENTRYPOINT [".venv/bin/python", "-m", "awslambdaric"]
CMD ["handler.handler"]
