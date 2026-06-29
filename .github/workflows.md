# CI/CD Workflows

> **Contributor reference**: this is CI/CD context, not the project README. For the project overview, see the [root README.md](../README.md).

## Branch Strategy

```mermaid
graph LR
    F[feat/*] -->|PR| D[develop]
    D -->|PR| M[main]
    M -->|tag v*| T[Deploy]
```

All work flows through pull requests. No direct pushes to `develop` or `main`.

## Workflows

| File | Trigger | Purpose |
|------|---------|---------|
| `ci.yml` | PR to `develop` | Lint, test, build (quality gate) |
| `promote.yml` | PR to `main` / push to `main` | Full suite + GHCR image push |
| `release.yml` | Manual (`workflow_dispatch`) on `main` | Create version tag + GitHub Release with changelog |
| `deploy.yml` | Tag `v*` pushed (by release workflow) | Build image, push to ECR, ECS Express Mode auto-deploys |

## Promotion Flow

```mermaid
sequenceDiagram
    participant Dev as Developer
    participant F as feat/* branch
    participant D as develop
    participant M as main
    participant R as Release workflow
    participant ECR as ECR
    participant ECS as ECS Express Mode

    Dev->>F: commit work
    F->>D: PR (ci.yml runs)
    Note over D: Python checks + UI checks + Docker build
    D->>M: PR (promote.yml runs)
    Note over M: Full test suite + e2e + GHCR push
    Dev->>R: Manual trigger: "Create Release v0.1.0"
    R->>M: Creates tag v0.1.0 + GitHub Release
    Note over R: Generates changelog from merged PRs
    M->>ECR: deploy.yml pushes image
    ECR->>ECS: ECS Express Mode auto-deploys
    Note over ECS: Health check, swap or rollback
```

## Release Process

Tags can only be created via the Release workflow (protected by tag ruleset).
No manual `git tag` + `git push` is allowed.

1. Ensure all work is merged to `main` via develop
2. Go to Actions, Release, Run workflow
3. Input version (semver, e.g., `0.1.0`)
4. Optionally check "dry run" to preview changelog
5. Workflow creates tag, GitHub Release with auto-changelog, triggers deploy

## CI on develop (`ci.yml`)

Runs on every PR targeting `develop`. Path-detection skips irrelevant jobs.

```mermaid
graph TD
    A[PR opened/updated] --> B[Detect changed paths]
    B -->|shelterpulse/ tests/ pyproject.toml| C[Python checks]
    B -->|ui/| D[UI checks]
    B -->|Dockerfile docker-compose.yml| E[Docker build]
    C --> E
    D --> E
```

**Python checks** (composite action `.github/actions/ci-python/`):
- `uv sync --all-groups`
- `tox -e lint`: pyrefly type checking
- `tox -e security`: bandit scan
- `tox -e test`: pytest unit tests with coverage

**UI checks** (composite action `.github/actions/ci-ui/`):
- `npm ci`
- `npm run type-check`
- `npm run lint`
- `npm run build`
- Cypress smoke test against static export

**Docker build**: builds the image without pushing (validates Dockerfile is sound).

## Promotion to main (`promote.yml`)

Runs on PRs targeting `main` and on push to `main` (after merge).

```mermaid
graph TD
    A[PR to main] --> B[Python checks]
    A --> C[UI checks]
    A --> D[E2E tests]
    B --> E{All pass?}
    C --> E
    D --> E
    E -->|yes| F[Merge allowed]
    F --> G[Push to main triggers image build]
    G --> H[Push to GHCR :latest + :sha-xxx]
```

**E2E tests**: docker compose up, pytest e2e suite, compose down.

## Deploy (`deploy.yml`)

Triggered automatically when the Release workflow pushes a `v*` tag.

```mermaid
graph TD
    A[Tag v1.2.3 pushed by Release workflow] --> B[Authenticate AWS via OIDC]
    B --> C[Login to ECR]
    C --> D[Build + push consolidated app image to ECR]
    D --> E[ECS Express Mode detects new image]
    E --> F{Health check passes?}
    F -->|yes| G[Traffic shifts to new task revision]
    F -->|no| H[Auto-rollback to previous revision]
```

## Composite Actions

Located in `.github/actions/`:

| Action | Used by | What it does |
|--------|---------|--------------|
| `ci-python/` | ci.yml, promote.yml | Install uv, sync deps, run lint + security + tests |
| `ci-ui/` | ci.yml, promote.yml | Install node, npm ci, type-check + lint + build + Cypress |
| `ci-docker/` | promote.yml | Build and push image to GHCR |

## Required Secrets and Variables

| Name | Where | Purpose |
|------|-------|---------|
| `GITHUB_TOKEN` | Built-in | GHCR authentication |
| `AWS_ROLE_ARN` | Repository secret | OIDC role for AWS access |

No static AWS credentials stored: authentication uses GitHub OIDC, IAM role assumption.

## Adding Required Status Checks

After workflows have run at least once, add required status checks to branch rulesets:

- **develop ruleset**: require `Python checks`, `UI checks`
- **main ruleset**: require `Python checks`, `UI checks`, `E2E tests`
