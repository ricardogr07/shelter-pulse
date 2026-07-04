# Security Scan Reports

**Date:** 2026-06-27  
**Tools:** pip-audit 2.10.1 (Python deps), npm audit (JS deps)

## pip-audit: Python dependencies

**Result: No known vulnerabilities found.**

All 80+ Python dependencies scanned against OSV database. Zero CVEs.

See: `pip-audit.json`

## npm audit: JavaScript dependencies

**Result: 2 moderate severity vulnerabilities** (both in Next.js bundled PostCSS)

| Advisory | Package | Severity | Fix |
|---|---|---|---|
| GHSA-qx2v-qp2m-jg93 | postcss < 8.5.10 (bundled in next@16.2.9) | Moderate | Would require downgrading to next@9: not viable |

**Accepted risk:** The PostCSS XSS advisory applies to CSS stringify output in server-rendered contexts. This project uses `output: "export"` (static site generation): no server-side CSS stringification occurs at runtime. The attack surface does not apply.

`npm audit fix --force` would downgrade Next.js to 9.3.3, breaking the app. Risk accepted.

See: `npm-audit.json`

## Aikido Security Scan - Round 2

**Date:** 2026-07-04
**Result:** 1 critical, 2 high, 4 medium, 2 low (8 resolved, 1 dropped)

| Finding | Severity | Category | Response |
|---|---|---|---|
| CSP header not set | Critical | DAST | Fixed: added `Content-Security-Policy` to `deploy/nginx-app.conf`. `script-src`/`style-src` need `'unsafe-inline'` - Next.js App Router's RSC hydration payload ships as inline `<script>` blocks, and React's inline `style={{...}}` bars set the attribute via the DOM, neither of which is nonce/hash-able on a static export. No third-party origins are used, verified directly against the built HTML and by loading every page in headless Chrome with zero CSP console violations. |
| HSTS header is missing | High | DAST | Fixed: added `Strict-Transport-Security: max-age=31536000; includeSubDomains` |
| Automatic upgrades of base Docker images can lead to supply chain attacks (`rabbitmq.Dockerfile`) | High | IaC | Fixed: pinned `alpine:latest` -> `alpine:3.24` |
| Docker container runs as default root user (`rabbitmq.Dockerfile`, `Dockerfile`) | Medium | IaC | Fixed: `rabbitmq.Dockerfile` runs as the `rabbitmq` user the alpine package already creates; `Dockerfile`'s `api` target runs as a new non-root `apiuser` (only `/app/data`, the DuckDB volume mount, needed a chown - the rest of `/app` stays root-owned but world-readable, avoiding a full recursive chown of the venv) |
| Missing Anti-clickjacking header | Medium | DAST | Fixed: added `X-Frame-Options: DENY` |
| Binary, code or archive is pulled from a remote source without integrity verification (`deploy.yml`) | Medium | Supply Chain | Actually fixed this time - see note below |
| SQS queue data is not encrypted (`main.tf`) | Low | IaC | Fixed: `sqs_managed_sse_enabled = true` on both the jobs queue and DLQ (AWS-managed key, no KMS to provision) |
| `actions/checkout` persists Git credentials (`auto-release.yml`, `release.yml`) | Low | Supply Chain | `release.yml` already an accepted risk (see below); `auto-release.yml` added to the same accepted-risk entry - it also pushes a git tag (`git push origin "v$VERSION"`), so it has the same real requirement |
| GitHub organization should enforce an IP allow list | Medium | Org config | Dropped: not a repo/code finding, it's a GitHub org/account setting. IP allow-listing for org access is a GitHub Enterprise Cloud feature that may not even be available on this account's plan, and configuring it wrong risks locking out the only maintainer. Left to manual review outside this project's code. |

**Note on the integrity-verification finding:** the round-1 "fix" below (added 2026-06-29) turned out not to work. The GPG verification step had `|| true` and `|| echo "::warning"` fallbacks that silently swallowed *any* verification failure and let the AWS CLI install proceed anyway - it looked like it verified, but never actually blocked on a bad signature. Worse, the hardcoded key fingerprint (`...180E282A1C0`) didn't even match the real AWS CLI signing key (verified directly against a live download: the actual fingerprint is `FB5DB77FD5C118B80511ADA8A6310ACC4672475C`), so a strict version of the old check would have failed permanently - which is almost certainly *why* the silent fallbacks were added in the first place, rather than fixing the real key. Round 2 fixes both: corrected fingerprint, and verification failures now fail the job (a bounded 3-attempt retry only covers the keyserver-reachability step, not a bad signature).

## Aikido Security Scan - Round 1

**Date:** 2026-06-29
**Result:** 0 critical, 4 high, 2 medium, 1 low (all resolved)

| Finding | Severity | Category | Response |
|---|---|---|---|
| `dangerouslySetInnerHTML` XSS in HowItWorksClient.tsx | High | SAST | Fixed: replaced with `katex.render()` DOM API |
| DynamoDB backups off | High | IaC | Fixed: enabled `point_in_time_recovery` in bootstrap/main.tf |
| ECR not encrypted at rest | High | IaC | Fixed: added `encryption_configuration` (AES256) in app-runner/main.tf |
| 3rd party GitHub Actions unpinned | High | Supply Chain | Fixed: all actions pinned to full SHA with version comment |
| Docker container runs as root | Medium | IaC | Fixed: added non-root `appuser`, nginx listens on 8080 |
| Binary pulled without integrity check | Medium | Supply Chain | Attempted fix was incomplete - see Round 2 above |
| `actions/checkout` persist-credentials | Low | Supply Chain | Fixed: added `persist-credentials: false` to all workflows (except release.yml which needs git push) |
| License management non-compliant | Low | License | Fixed: added Apache-2.0 LICENSE file to repo root |

## Accepted Risks (all intentional for hackathon demo)

| Risk | Justification |
|---|---|
| CORS wildcard (`allow_origins=["*"]`) | Demo API; production would restrict to UI domain |
| `pickle.load` for demo cache | `whisker_haven_cache.pkl` is a trusted build artifact generated by `scripts/precompute_demo.py` from local scenario data. No user-controlled input is deserialized. |
| PostCSS CVE in Next.js bundle | Static export context; XSS vector doesn't apply (see above) |
| `release.yml` and `auto-release.yml` retain persist-credentials | Both push git tags (`git push origin v$VERSION`); restricted to `workflow_dispatch`/push-to-main respectively, not exposed to arbitrary PR code |
| GitHub org IP allow list not enforced | GitHub Enterprise Cloud feature, may not be available on this account's plan; manual account-level setting outside this project's code, left to the maintainer's own judgment on IP ranges |
