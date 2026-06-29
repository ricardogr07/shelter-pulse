# Worker: CLI

**Model:** Claude Haiku 4.5 | **Effort:** low | **Phase:** any

**Role:** Maintain and extend `shelterpulse/cli/main.py`. File already exists.

## File You Own

- `shelterpulse/cli/main.py` (extend only)

Forbidden zones: core/, optimize/ (read-only), api/, ui/, .github/workflows/

## Current Commands (DO NOT re-implement)

```bash
uv run python -m shelterpulse.cli.main --help
# simulate   Run a single simulation
# optimize   Run full optimization sweep
# baselines  Show 5 named baseline allocations
# export     Export results to YAML+CSV
```

## How to Add a Command

```python
@app.command()
def my_command(
    param: int = typer.Option(4, help="description"),
) -> None:
    from shelterpulse.core.schema import load_scenario  # lazy import
    scenario = load_scenario()
    # thin wrapper: call into core or optimize, print result
    typer.echo(result)
```

Rules:
- Lazy imports inside command bodies (avoid circular import risk at module load)
- No business logic in cli/main.py -- thin wrapper only
- No `--scenario` flag (Whisker Haven hardcoded via `load_scenario()`)
- No new typer options unless the issue explicitly requests them

## How to Test

```bash
uv run python -m shelterpulse.cli.main --help          # shows 4+ commands
uv run python -m shelterpulse.cli.main baselines       # prints table
uv run python -m shelterpulse.cli.main simulate --reps 4
uv run python -m shelterpulse.cli.main optimize --candidates 4 --reps 4 --no-bo
```
