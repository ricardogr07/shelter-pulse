# Security Scan Reports

**Date:** 2026-06-27
**Tools:** pip-audit (Python deps), npm audit (JS deps)

## Results

- pip-audit: see pip-audit.json (or pip-audit.txt)
- npm audit: see npm-audit.json

## Accepted Risks

- CORS wildcard (`allow_origins=["*"]`) — intentional for hackathon demo.
  Production deployments should restrict to the UI domain.
- No authentication on API endpoints — demo/hackathon scope.
  Production would add OAuth2/JWT.
