# ADR-007: Deploy API and UI as Separate Render Web Services

> **SUPERSEDED by [ADR-011](011-ecs-express-mode.md)** (via ADR-008). Kept for decision trail.

**Status:** Superseded by [ADR-008](008-aws-app-runner.md) | **Date:** 2026-06-26

## Context

ShelterPulse has two runnable artifacts: the FastAPI API (port 8000) and the nginx-served
Next.js static export (port 80). The `Dockerfile` has named targets for each. We need a
public URL accessible to hackathon judges without any auth.

## Decision

Two Render Web Services, both from the same repo and `Dockerfile`:

| Service | Docker target | Port | URL pattern |
|---------|--------------|------|-------------|
| `shelterpulse-api` | `api` | 8000 | `shelterpulse-api.onrender.com` |
| `shelterpulse-ui` | `ui` | 80 | `shelterpulse-ui.onrender.com` |

The UI build receives `NEXT_PUBLIC_API_URL` as a build-time env var pointing at the API
service URL. This is baked into the static export at build time (Next.js `output: "export"`
has no server-side runtime, so runtime env vars are unavailable).

## Consequences

- Cold-start latency on free tier (~30s). Acceptable for demo; note in README.
- Build arg is baked at image build time: changing the API URL requires rebuilding the UI.
- No ingress/reverse-proxy layer needed: Render handles TLS termination.
- CORS wildcard in API remains appropriate (UI and API are on different origins).
