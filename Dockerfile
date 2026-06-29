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


# --- Consolidated target (uvicorn + nginx in one image) for ECS Express Mode ---
# Reuses the `api` stage (venv + uvicorn), adds nginx to serve the static UI and
# reverse-proxy /api/* to uvicorn. Build the UI with NEXT_PUBLIC_API_URL=/api so the
# browser calls a same-origin relative path (no CORS, no build-time API URL coupling).
FROM api AS app

RUN apt-get update \
    && apt-get install -y --no-install-recommends nginx \
    && rm -rf /var/lib/apt/lists/* \
    && rm -f /etc/nginx/sites-enabled/default

# Non-root: nginx listens on 8080; ECS Express maps containerPort 8080 → ALB 80/443
RUN useradd -r -s /bin/false appuser \
    && mkdir -p /var/log/nginx /var/lib/nginx/body /run \
    && chown -R appuser:appuser /var/log/nginx /var/lib/nginx /run \
    && sed -i 's|/var/run/nginx.pid|/run/nginx.pid|' /etc/nginx/nginx.conf

COPY --from=ui-build /app/out /usr/share/nginx/html
COPY deploy/nginx-app.conf /etc/nginx/conf.d/default.conf
COPY deploy/start.sh /start.sh
RUN chmod +x /start.sh && chown -R appuser:appuser /usr/share/nginx/html

USER appuser

EXPOSE 8080
CMD ["/start.sh"]
