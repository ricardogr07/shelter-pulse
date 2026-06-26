# ADR-002: Use Next.js + React + TypeScript + Tailwind CSS for the UI

**Status:** Accepted | **Date:** 2026-06-26

## Context

The scope lock §5.4 defaulted to Streamlit for the UI because it offered the fastest path
from a working core to a presentable UI under time pressure. However, the developer
explicitly wants to lock in Next.js + React + TypeScript + Tailwind CSS and accepts the
additional ~8–12 h of UI work this implies.

## Decision

The `ui/` directory is a Next.js 15 app with:
- TypeScript (strict mode)
- Tailwind CSS
- App Router
- Cypress for e2e browser testing

The backend API (FastAPI) is the single integration point; the UI communicates only via
`/api/*` HTTP calls. This preserves the clean adapter boundary from the architecture.

## Consequences

- Richer, more customizable UI than Streamlit; better fit for the UX/UI judging category.
- Adds ~8–12 h of frontend work relative to Streamlit baseline. Accepted.
- Cypress e2e tests cover the full browser → API → core path.
- Static export (`next export`) is possible if the deployment host prefers static files.
- **Supersedes** scope lock §5.4 Streamlit default.
