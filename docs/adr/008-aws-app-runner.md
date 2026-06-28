# ADR-008: Switch Cloud Deployment from Render to AWS App Runner

**Status:** Accepted (supersedes ADR-007) | **Date:** 2026-06-26

## Context

ADR-007 chose Render for its one-click simplicity. However:
- The team already uses AWS tooling and wants to stay in a single cloud ecosystem.
- AWS Free Plan gives $200 in credits for 6 months — more than enough for a demo workload.
- App Runner provides comparable PaaS simplicity (push image → get HTTPS URL) without vendor lock to a smaller platform.
- Render free tier has aggressive cold-start latency (~30s) that could frustrate judges.

## Decision

Deploy both services (API + UI) to **AWS App Runner**, pulling images from **Amazon ECR**.

| Service | ECR Repo | App Runner Config | Port |
|---------|----------|-------------------|------|
| `shelterpulse-api` | `shelterpulse-api` | 0.25 vCPU / 0.5 GB | 8000 |
| `shelterpulse-ui` | `shelterpulse-ui` | 0.25 vCPU / 0.5 GB | 80 |

Deployment is deferred to Wave 2b — all local work (security scan, demo script, .kiro commit) completes first.

## Consequences

- Requires AWS account creation (Free Plan, credit card for verification only).
- Cold start still exists on App Runner but is typically 5-15s (better than Render free).
- More setup steps than Render (ECR push + IAM role), but fully scriptable via AWS CLI.
- $200 credits cover ~40 months of idle provisioned instances — no risk of charges.
- `NEXT_PUBLIC_API_URL` is still baked at UI build time (same constraint as Render).
- ADR-007 is now superseded.
