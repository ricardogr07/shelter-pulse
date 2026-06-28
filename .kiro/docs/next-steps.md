# Next Steps — Phase 0 Completion + App Runner Deploy

## Status as of 2026-06-27

### ✅ Completed

| Task | PR | Notes |
|------|----|-------|
| Branch strategy + .gitignore | #2 | develop + main protected, no force push |
| CI workflow (PRs to develop) | #2 | Path-detected: python, ui, docker |
| Promote workflow (PRs to main + GHCR) | #2 | Full suite + GHCR push on merge |
| Terraform state backend | #3 | S3 + DynamoDB in us-east-1 |
| GitHub OIDC role | #5 | Keyless AWS auth from Actions |
| ECR + App Runner IAM | #6 | Image repo ready, lifecycle policies |
| Release + Deploy workflows | #7 | Manual release → auto deploy to ECR |
| pyrefly fix for optional jax | #9 | CI fully green |
| Release workflow fixes (identity, OIDC, version) | #10 | All Codex review items addressed |
| First release v0.1.0 | — | Image in ECR ✅, GitHub Release created ✅ |
| Promote to main (Phase 0) | #8 | Merged, GHCR push successful |

### ⏳ Blocked (AWS account activation — wait 24h)

- **App Runner service creation** — `SubscriptionRequiredException`
- Account created today, AWS needs up to 24h to fully activate services

### 📋 Remaining Tasks (no blockers)

| Task | Description |
|------|-------------|
| Task 8 | PyPI package structure + Trusted Publisher workflow |
| Task 9 | Documentation under .kiro/docs/ + GitHub manual config guide |

---

## Tomorrow: App Runner Deploy

Once AWS account is active, run:

```powershell
$env:PATH = "C:\Program Files\Amazon\AWSCLIV2;" + $env:PATH
$env:AWS_PROFILE = "shelterpulse"
$env:GODEBUG = "netdns=go"
terraform -chdir=C:\git\shelter-pulse\infra\app-runner apply -auto-approve
```

Expected output: `app_url = "https://<id>.us-east-1.awsapprunner.com"`

Then verify:
```
curl https://<url>/health    → {"status": "ok"}
curl https://<url>/docs      → FastAPI OpenAPI docs
```

## Tomorrow: Commit App Runner Terraform Change

The `infra/app-runner/main.tf` has the App Runner service resource added locally but not committed. After successful deploy:

1. Create branch: `git checkout -b feat/app-runner-service`
2. Commit: `git add infra/app-runner/main.tf && git commit -m "infra: add App Runner service (blue/green, auto-deploy from ECR)"`
3. Push + PR to develop → merge → PR to main → merge

## After Phase 0: Ship What's On Disk → Develop

Sequential PRs shipping existing untracked files (no new implementation):

| # | Branch | Scope |
|---|--------|-------|
| 1 | `feat/kiro-config` | .kiro/ steering + agents + docs |
| 2 | `feat/optimizer-tests` | GP optimizer tests + precompute script |
| 3 | `feat/ui-components` | NavBar, charts, i18n (en+es), [lang] pages |
| 4 | `feat/docker-infra` | .dockerignore + nginx.conf |
| 5 | `feat/docs-security` | ADRs 007-010, architecture docs, security audits |
| 6 | `feat/app-runner-service` | infra/app-runner/main.tf modification |
| 7 | `feat/remaining-tests` | CLI, sensitivity, timeline, uncertainty tests |

Full details: `.kiro/docs/pr-commit-plan.md`
Post-merge implementation work: `docs/post-merge-backlog.md`

## Key Info (local only, not in git)

- AWS CLI profile: `shelterpulse` (configured in ~/.aws/credentials)
- Terraform state: `s3://shelterpulse-tfstate/` (us-east-1)
- GitHub secret: `AWS_ROLE_ARN` (set via gh cli)
- Tag ruleset: blocks deletion + force-update of v* tags, allows creation
