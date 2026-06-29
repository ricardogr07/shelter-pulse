# Deployment Architecture

## Local development (docker compose up)

```mermaid
graph TB
  subgraph host["Developer Machine / Judge Laptop"]
    subgraph compose["docker compose"]
      nextjs["nextjs\n:3000\nNext.js production build"]
      fastapi["fastapi\n:8000\nUvicorn + FastAPI"]
      temporal_svc["temporal\n:7233\nTemporal dev server\n(profile: temporal: disabled by default)"]
      temporal_ui["temporal-ui\n:8080\nTemporal Web UI\n(profile: temporal)"]
    end
    browser["Browser"] -->|http://localhost:3000| nextjs
    browser -->|http://localhost:8000/docs| fastapi
    nextjs -->|HTTP /api/*| fastapi
    fastapi -->|gRPC| temporal_svc
    temporal_ui -->|gRPC| temporal_svc
  end
```

Enable Temporal services:
```bash
docker compose --profile temporal up
```

## Cloud deployment (Phase 3)

```mermaid
graph LR
  subgraph internet["Public Internet"]
    judge["Judge Browser"]
  end

  subgraph cloud["Cloud Host\n(Render / Railway / Fly.io)"]
    cdn["CDN / Edge\n(Next.js static export\nor SSR service)"]
    api_svc["FastAPI service\n(containerized)"]
  end

  judge -->|HTTPS :443| cdn
  cdn -->|internal| api_svc
```

**Deployment strategy:**
- FastAPI container built from `Dockerfile` (Python 3.12-slim base)
- Next.js either: (a) built as static export served from FastAPI's static files, or
  (b) deployed as a separate service on the same host
- Choice made at deployment time (Phase 3) based on host friction
- No secrets beyond a deploy token: synthetic data only, no auth

## Dockerfile targets

```mermaid
graph LR
  base["python:3.12-slim\n(base)"] --> api_img["api target\nuv install + uvicorn"]
  node_base["node:20-alpine\n(build stage)"] --> ui_build["npm ci + next build"]
  ui_build --> ui_img["ui target\nnginx:alpine + static export"]
```
