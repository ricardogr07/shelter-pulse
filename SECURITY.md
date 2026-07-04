# Security Policy

## Data handling

ShelterPulse operates exclusively on **synthetic data**. It contains no real animal records,
no employee records, and no personally identifiable information. The demo scenario (Whisker Haven)
is entirely fictional. There is no authentication requirement for the public demo instance
because there is nothing sensitive to protect.

## Threat surface

- The REST API accepts scenario YAML as structured input validated by Pydantic v2.
  Malformed or adversarial input is rejected at the validation layer with a 422 response.
- No `eval`, no arbitrary file paths from user input, no shell execution.
- Dependencies are pinned in `uv.lock` and scanned by Aikido on every push.

## Security scan

Full results, per-finding remediation, and accepted-risk justifications are in
[`security/README.md`](security/README.md).

| Scan date | Tool | Result |
|---|---|---|
| 2026-06-29 | Aikido | 0 critical, 4 high, 2 medium, 1 low — all resolved |
| 2026-06-29 | pip-audit | No known vulnerabilities (80+ Python dependencies) |
| 2026-06-29 | npm audit | 2 moderate (bundled Next.js PostCSS); accepted risk, does not apply under static export |

A final scan is planned before submission to cover dependencies added after
this date.

## Reporting a vulnerability

This is a hackathon project. If you find a security issue, open a GitHub issue labelled `security`.
