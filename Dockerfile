# --- API target ---
FROM python:3.12-slim AS api

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency files first for layer caching
COPY pyproject.toml uv.lock ./
RUN uv sync --no-dev --no-install-project

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
EXPOSE 80
