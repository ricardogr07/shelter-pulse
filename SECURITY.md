# Security Policy

## Data handling

ShelterPulse operates exclusively on **synthetic data**. It contains no real animal records,
no employee records, and no personally identifiable information. The demo scenario (Whisker Haven)
is entirely fictional. There is no authentication requirement for the public demo instance
because there is nothing sensitive to protect.

## Threat model

**Assets:** synthetic scenario data; the opt-in run-history/consent log in DuckDB
(also synthetic); the `INTERNAL_KEY` webhook shared secret; the AWS infrastructure
and its IAM roles; the GitHub Actions OIDC deploy role.

**Trust boundaries / entry points:**

| Entry point | Exposure | Auth |
|---|---|---|
| Public HTTPS (`/en`, `/api/*`) | Anonymous, internet-facing | None (nothing sensitive to protect); per-IP rate limiting on concurrent jobs |
| Internal webhook (`/internal/jobs/*`) | Called only by the Lambda/RabbitMQ worker, not by browsers | `X-Internal-Key` shared secret |
| CI/CD (GitHub Actions) | Deploy role assumed via OIDC, no long-lived AWS keys | Narrowly scoped to ECR, ECS Express, and one named Lambda function ARN |
| Terraform-managed infra | Applied manually from a developer machine | Not part of automated CI |

**Threats considered and their controls:**

- Adversarial/malformed API input -> Pydantic v2 validation at every boundary, 422 on rejection; no `eval`, no arbitrary file paths from user input, no shell execution.
- Endpoint abuse / compute-exhaustion DoS on the optimize endpoints -> per-IP concurrent-job limit (`count_active_by_ip`), 5-minute job TTL sweep so a stuck job can't hold a slot indefinitely.
- Cross-site scripting -> Content-Security-Policy, no `dangerouslySetInnerHTML` anywhere in the UI.
- Clickjacking -> `X-Frame-Options: DENY`.
- Transport downgrade -> HSTS.
- Internal webhook forgery -> shared-secret header, path not reachable from the public internet except via the NAT-routed Lambda that holds the secret.
- Supply chain -> dependencies pinned in `uv.lock` and scanned periodically by Aikido (manual/scheduled scans; instant on-push scanning is a paid Aikido tier this project doesn't use), pip-audit/npm-audit, GitHub Actions pinned to full commit SHAs, Docker base images pinned to versioned tags (not `:latest`), AWS CLI download integrity verified by GPG signature against the correct published key.
- Container/host privilege -> every runtime container (API, worker, RabbitMQ, the consolidated production image) runs as a non-root user.
- Data at rest -> SQS (SSE-SQS), EFS, and ECR are all encrypted.

**Residual risks:** see the Accepted Risks table in
[`security/README.md`](security/README.md) rather than duplicating it here -
that's the single source of truth for what's knowingly left unaddressed and why.

## Security scan

Full results, per-finding remediation, and accepted-risk justifications are in
[`security/README.md`](security/README.md). Aikido's own issue export/report
download is a paid-tier feature not available on this project's plan, so
this file is the authoritative record of what each scan found and how it was
resolved.

| Scan date | Tool | Result |
|---|---|---|
| 2026-07-04 | Aikido | 1 critical, 2 high, 4 medium, 2 low — 8 resolved, 1 dropped (org-level IP allow list, not code-fixable, left to manual review) |
| 2026-06-29 | Aikido | 0 critical, 4 high, 2 medium, 1 low — all resolved |
| 2026-06-29 | pip-audit | No known vulnerabilities (80+ Python dependencies) |
| 2026-06-29 | npm audit | 2 moderate (bundled Next.js PostCSS); accepted risk, does not apply under static export |

## Reporting a vulnerability

This is a hackathon project with no dedicated security contact, but please still report
privately rather than in a public issue: use GitHub's private vulnerability reporting
(this repository's **Security** tab -> **Report a vulnerability**). Given the synthetic-data
scope above, most findings will be about infrastructure/dependency hygiene rather than data
exposure, but the private channel avoids giving a working exploit a public audience before
a fix lands.
