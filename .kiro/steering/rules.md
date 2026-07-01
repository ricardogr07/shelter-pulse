---
inclusion: always
---

# ShelterPulse: Agent Rules (Non-Negotiable)

These rules apply to ALL agents working on this project. Violating any of them may break the submission.

## 1. Conservation test is sacred

After any change to `core/engine.py`, run:
```bash
uv run pytest tests/unit/test_conservation.py -v
```
**This test must pass.** It verifies that every cat that enters the shelter exits via a terminal state (adopted, transferred, or still_in_shelter). A failure here means the simulation is fundamentally broken.

## 2. No new packages without orchestrator approval

- No `pip install X` / `uv add X` that modifies `pyproject.toml` or `uv.lock`
- No `npm install X` that modifies `ui/package.json`
- If a spec requires a package that isn't already installed, **stop and ask**

## 3. No git operations except diff and status

Workers may:
```bash
git diff HEAD          # review what was changed
git status             # check working tree
uv run pytest ...      # run tests
```

Workers must NOT:
```bash
git add / git commit   # orchestrator only
git push               # orchestrator only
git reset --hard       # orchestrator only
git commit --amend     # orchestrator only
```

## 4. No changes to CI/CD or workflows

Files in `.github/workflows/` are orchestrator-only. Never touch them.

## 5. Mark done in STATUS.md

When a task is complete, edit `.localagent/docs/STATUS.md`:
- Set your track's Status to `DONE`
- Fill in the Tests column with which pytest commands passed
- Note any issues in the Notes column

## 6. Minimum code (ponytail constraint)

Write the minimum code that satisfies the spec. No:
- Interfaces with one implementation
- Config values that never change
- Helper classes that wrap a single function
- Abstractions for hypothetical future cases

The spec in `.localagent/docs/<spec>.md` defines exactly what's needed. Stay within it.

## 7. Forbidden zones per role

Each worker has an explicit file ownership list in `.localagent/agents/worker-*.md`. Only edit files you own. If a change requires touching a file owned by another worker, coordinate via STATUS.md notes.

## 8. Run tests before marking done

A task is not DONE until the relevant tests pass. Don't mark DONE and leave failing tests.

## 9. Read the Next.js warning (UI worker only)

Before writing any code in `ui/`, read `ui/AGENTS.md`. This Next.js version has breaking changes vs. training data. The file tells you where to find the real docs.

## 10. Speak in domain language

Use: cats, kittens, isolation queue, foster placement, vet tech, adoption counselor, Whisker Haven.
Avoid: entities, units, agents (unless referring to AI agents), generic terms.


## 11. Dockerized testing before push

Before pushing any branch that modifies backend code, infrastructure, or docker-compose:
1. Run `docker compose up --build -d` and verify all containers are healthy
2. Run integration tests: `uv run pytest tests/integration/ -v`
3. Verify both sync and async paths work
4. Check worker logs: `docker logs shelter-pulse-worker-1 --tail 10`

Skipping Docker verification has caused production issues. Do not skip.

## 12. Productionalization standards

When adding new infrastructure or services:
1. **Local first**: Must work in docker-compose before considering AWS deployment
2. **Feature flags**: New infra must have a fallback (e.g., QUEUE_BACKEND=sync)
3. **Cost awareness**: Stay within $100/month AWS budget. Prefer free tier services.
4. **Blue/green readiness**: Every deployment must be rollback-safe via image tag pinning
5. **No em dashes**: Never use em dashes (U+2014) in any user-facing copy, metadata, or comments. Use hyphens instead.

## 13. Container hygiene

- Production images must be lean: only install what the service actually needs
- Workers must use stdlib for HTTP calls (urllib.request) - no extra deps
- Always pin base image digests in CI, use tags in development
- Health checks must be defined for every service in docker-compose
- Retry logic with exponential backoff for all inter-service connections