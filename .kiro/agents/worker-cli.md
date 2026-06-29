# Worker: CLI: Typer Commands

**Model:** Claude Haiku 4.5 | **Effort:** medium  
**Depends on:** Core-A (interventions) + Core-B (montecarlo) must be DONE  
**Parallel with:** API worker (worker-api.md)

## Role

Implement the Typer CLI. Four commands: `simulate`, `optimize`, `baselines`, `export`. Thin wrapper over core: no logic here.

## Read first

```
@.localagent/agents/SHARED.md
@.localagent/docs/06-cli.md
```

## Files you own

| File | Action |
|------|--------|
| `shelterpulse/cli/main.py` | **Create** |

No new test file needed: use the smoke checks in done criteria.

## Files you must NOT touch

- `core/*.py`
- `optimize/*.py`
- `api/app.py`: owned by API worker
- `ui/`
- `pyproject.toml` entry point `shelterpulse = "shelterpulse.cli.main:app"`: already correct, don't change it

## Done criteria

- [ ] `uv run shelterpulse --help` shows 4 commands: simulate, optimize, baselines, export
- [ ] `uv run shelterpulse baselines` prints 4 named baseline rows without error
- [ ] `uv run shelterpulse simulate --reps 4` completes without error
- [ ] `uv run shelterpulse optimize --candidates 4 --reps 4 --no-bo` completes in < 60 seconds
- [ ] Update `.localagent/docs/STATUS.md` row for CLI

## Key rules

- All imports from core/optimize are **inside the command functions** (lazy imports): this way CLI works even if some optional deps are missing
- `export` command imports `core.export.export_results` lazily: if Core-D isn't merged yet, import fails gracefully
- No `--scenario` flag: Whisker Haven is hardcoded per scope lock §2.3
- The `pyproject.toml` script entry `shelterpulse = "shelterpulse.cli.main:app"` must be the Typer `app` object
