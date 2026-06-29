# Playbook: Working on a GitHub Issue

Standard operating procedure for every code change. Start here before writing any code.

## 1. Find and read the issue

```bash
# List open issues for a phase
gh issue list --repo ricardogr07/shelter-pulse --label "phase:<N>" --state open

# Read a specific issue
gh issue view <number> --repo ricardogr07/shelter-pulse
```

## 2. Move to In Progress in GitHub Project

GitHub Project #5: https://github.com/users/ricardogr07/projects/5

Set the Status field to "In Progress" for the issue card.

## 3. Assign to self

```bash
gh issue edit <number> --repo ricardogr07/shelter-pulse --add-assignee @me
```

## 4. Create feature branch

Branch naming: `feat/issue-<number>-<short-slug>`

```bash
git checkout develop && git pull origin develop
git checkout -b feat/issue-<number>-<short-slug>
# Example: feat/issue-36-bo-comparison-panel
```

## 5. Read the relevant spec

- Issue body: check for source spec reference (usually `.localagent/docs/PHASE-<N>/<track>.md`)
- Worker file: `.kiro/agents/worker-<domain>.md` for your domain
- Architecture invariants: `.kiro/steering/architecture.md`

## 6. Implement

- Follow ponytail constraints: YAGNI → reuse existing code → stdlib → minimum new code
- Type annotations everywhere
- Run after every meaningful change:
  ```bash
  uv run pytest tests/unit/ -v
  tox -e lint
  ```

## 7. Commit with issue reference

```bash
git add <specific-files-only>
git commit -m "feat: <short description>

Closes #<issue-number>"
```

`Closes #N` in the commit body (or PR body) auto-closes the issue on merge.

## 8. Push and create PR

```bash
git push -u origin feat/issue-<number>-<short-slug>

gh pr create --repo ricardogr07/shelter-pulse \
  --base develop \
  --title "feat: <description>" \
  --body "$(cat <<'EOF'
## Summary

<!-- one sentence -->

## Closes
- #<issue-number>

## Checklist
- [ ] tox -e lint passes
- [ ] tox -e test passes
- [ ] tox -e security passes
- [ ] cd ui && npm run build passes (if UI changed)
- [ ] No new pip/npm packages added without approval
- [ ] No em dashes in any committed document
- [ ] No #hackthekitty/ files staged
EOF
)"
```

## 9. After CI passes and PR merges

- GitHub auto-closes the linked issue (via `Closes #N`)
- Move issue card to Done in GitHub Project (if not auto-updated)
- Clean up:
  ```bash
  git checkout develop && git pull origin develop
  git branch -d feat/issue-<number>-<short-slug>
  ```
