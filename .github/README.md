# CI/CD Workflows

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
| `ci.yml` | PR → `develop` | Lint, test, build (quality gate) |
| `promote.yml` | PR → `main` / push to `main` | Full suite + GHCR image push |
| `deploy.yml` | Tag `v*` | Push to ECR → App Runner blue/green |
| `publish-pypi.yml` | PR merge to `develop` touching `shelterpulse/core/` | Build + publish `shelterpulse-core` to PyPI |

## Promotion Flow

```mermaid
sequenceDiagram
    participant Dev as Developer
    participant F as feat/* branch
    participant D as develop
    participant M as main
    participant GHCR as GHCR
    participant ECR as ECR
    participant AR as App Runner

    Dev->>F: commit work
    F->>D: PR (ci.yml runs)
    Note over D: Python checks + UI checks + Docker build
    D->>M: PR (promote.yml runs)
    Note over M: Full test suite + e2e
    M->>GHCR: On merge: push image
    Dev->>M: Create tag v*
    M->>ECR: deploy.yml pushes image
    ECR->>AR: Auto-deploy (blue/green)
    Note over AR: Health check → swap or rollback
```

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
- `tox -e lint` — pyrefly type checking
- `tox -e security` — bandit scan
- `tox -e test` — pytest unit tests with coverage

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

**E2E tests**: docker compose up → pytest e2e suite → compose down.

## Deploy (`deploy.yml`)

Triggered by pushing a version tag (`v*`).

```mermaid
graph TD
    A[Tag v1.2.3 pushed] --> B[Authenticate AWS via OIDC]
    B --> C[Login to ECR]
    C --> D[Build + push image to ECR]
    D --> E[App Runner detects new image]
    E --> F{Health check passes?}
    F -->|yes| G[Traffic shifts to new revision]
    F -->|no| H[Auto-rollback to previous revision]
```

## Composite Actions

Located in `.github/actions/`:

| Action | Used by | What it does |
|--------|---------|--------------|
| `ci-python/` | ci.yml, promote.yml | Install uv, sync deps, run lint + security + tests |
| `ci-ui/` | ci.yml, promote.yml | Install node, npm ci, type-check + lint + build + Cypress |
| `ci-docker/` | promote.yml | Build and push image to GHCR |

## Required Secrets & Variables

| Name | Where | Purpose |
|------|-------|---------|
| `GITHUB_TOKEN` | Built-in | GHCR authentication |
| `AWS_ROLE_ARN` | Repository secret | OIDC role for AWS access |

No static AWS credentials stored — authentication uses GitHub OIDC → IAM role assumption.

## Adding Required Status Checks

After workflows have run at least once, add required status checks to branch rulesets:

- **develop ruleset**: require `Python checks`, `UI checks`
- **main ruleset**: require `Python checks`, `UI checks`, `E2E tests`
