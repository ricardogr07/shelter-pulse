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

Aikido security scan results are committed to `/security/` and linked here after Phase 4 hardening.

| Scan date | Tool | Result |
|---|---|---|
| _TBD_ | Aikido | _pending_ |

## Reporting a vulnerability

This is a hackathon project. If you find a security issue, open a GitHub issue labelled `security`.
