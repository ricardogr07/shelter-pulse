# Contributing to ShelterPulse

## Local setup

```bash
git clone https://github.com/ricardogr07/shelter-pulse.git
cd shelter-pulse
docker compose up          # UI at :3000, API at :8000
```

Or without Docker:
```bash
uv sync --all-extras       # Python deps
uv run pytest tests/unit/ -v
cd ui && npm install && npm run dev
```

## Branching convention

- Branch from `develop`, not `main`
- Prefix: `feat/`, `fix/`, `docs/`, `chore/`
- Open PR against `develop`
- `main` is the stable public branch, promoted via maintainer PR

## Before opening a PR

```bash
tox -e lint      # pyrefly type check
tox -e test      # full test suite
tox -e security  # bandit scan
cd ui && npm run build
```

All checks must pass. See [`.github/pull_request_template.md`](.github/pull_request_template.md) for the PR checklist.

## Dependency policy

No new `pip` or `npm` packages without maintainer approval (`@ricardogr07`). Every new dependency adds attack surface and build time.

## Questions?

Open a [GitHub Discussion](https://github.com/ricardogr07/shelter-pulse/discussions) or file an issue using the templates in `.github/ISSUE_TEMPLATE/`.
