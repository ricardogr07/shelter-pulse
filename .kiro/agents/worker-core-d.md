# Worker: Core-D: Reproducible Export

**Model:** Claude Haiku 4.5 | **Effort:** medium  
**Parallel with:** Core-A, Core-B, Core-C (can be done simultaneously)

## Role

Implement `core/export.py` which writes optimization results to YAML + CSV with full reproducibility metadata (scenario params, seed set, all results ranked).

## Read first

```
@.localagent/agents/SHARED.md
@.localagent/docs/07-export.md
```

## Files you own

| File | Action |
|------|--------|
| `shelterpulse/core/export.py` | **Create** |
| `tests/unit/test_export.py` | **Create** |

**Note:** The `/export` route for `api/app.py` is described in the spec but belongs to the API worker (worker-api). Leave a comment in your file noting this.

## Files you must NOT touch

- All other `core/*.py` files
- `optimize/*.py`
- `api/`, `cli/`, `ui/`

## Done criteria

- [ ] `uv run pytest tests/unit/test_export.py -v`: all tests pass
- [ ] `export_results(scenario, results, seeds, tmp_path)` writes both `results.yaml` and `results.csv`
- [ ] Calling it twice on the same `out_dir` does not error (overwrite, not append)
- [ ] YAML includes `scenario`, `seed_set`, and `results` keys
- [ ] CSV has one row per result with `rank` column
- [ ] Update `.localagent/docs/STATUS.md` row for Core-D

## Key contracts

```python
def export_results(
    scenario: Scenario,
    results: list[EvaluationResult],
    seed_set: list[int],
    out_dir: Path,
) -> list[Path]:  # returns [yaml_path, csv_path]
```

- No new dependencies: `yaml` (pyyaml, already installed) + `csv` (stdlib)
- Round floats to 2 decimal places in output files
- `rank` starts at 1 for the first result in the list
