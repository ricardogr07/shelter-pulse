# --- API target ---
FROM python:3.12-slim AS api

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency files first for layer caching
COPY pyproject.toml uv.lock ./
RUN uv sync --no-dev --no-install-project --extra optimize

# pyDOE shim: jaxbo imports `pyDOE` (old name); installed package is `pydoe` (new name)
RUN python -c "import site; sp=[p for p in site.getsitepackages() if 'site-packages' in p][0]; open(sp+'/pyDOE.py','w').write('from pydoe import *\nfrom pydoe import lhs\n')"

# Fix jaxbo compat with JAX 0.10+: jnp.clip(x, a_min=0) -> jnp.clip(x, 0, None)
RUN find /app/.venv -path '*/jaxbo/*.py' \
    -exec sed -i 's/np\.clip(\([^,]*\),\s*a_min=\([^,)]*\))/np.clip(\1, \2, None)/g' {} \;

# Copy source
COPY shelterpulse/ shelterpulse/
COPY scenarios/ scenarios/

# Add project root to Python path (avoids hatchling build-wheel step in image)
ENV PYTHONPATH=/app

EXPOSE 8000
CMD [".venv/bin/uvicorn", "shelterpulse.api.app:app", "--host", "0.0.0.0", "--port", "8000"]


# --- UI build stage ---
FROM node:20-alpine AS ui-build

WORKDIR /app
COPY ui/package.json ui/package-lock.json ./
RUN npm ci
COPY ui/ .
ARG NEXT_PUBLIC_API_URL=http://localhost:8000
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
RUN npm run build


# --- UI target (static export via nginx) ---
FROM nginx:alpine AS ui

COPY --from=ui-build /app/out /usr/share/nginx/html
COPY ui/nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
