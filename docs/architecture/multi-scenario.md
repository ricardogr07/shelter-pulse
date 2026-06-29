# Multi-Scenario Architecture (Phase 3)

Describes the data model and module additions that allow any shelter to load, store,
and compare custom scenarios: not just the hardcoded Whisker Haven.

---

## New module: `shelterpulse/store/`

```
shelterpulse/
  store/
    __init__.py
    models.py      # SQLAlchemy ORM models
    crud.py        # create / read / delete operations
    db.py          # engine + session factory (SQLite default)
```

`store/` is an **adapter**: same boundary rules as `api/` and `cli/`:
- May import from `shelterpulse.core` (to call `load_scenario`, validate Pydantic models)
- Must NOT be imported by `shelterpulse.core`
- `tests/unit/test_no_cross_imports.py` must be extended to cover `store/`

---

## SQLAlchemy models (`store/models.py`)

```python
class ScenarioRecord(Base):
    __tablename__ = "scenarios"
    slug: Mapped[str] = mapped_column(String, primary_key=True)   # e.g. "whisker-haven"
    name: Mapped[str] = mapped_column(String)
    yaml_content: Mapped[str] = mapped_column(Text)               # raw YAML stored as text
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    source: Mapped[str] = mapped_column(String, default="manual") # "manual" | "csv_import"

class RunRecord(Base):
    __tablename__ = "runs"
    id: Mapped[str] = mapped_column(String, primary_key=True)     # UUID
    scenario_slug: Mapped[str] = mapped_column(ForeignKey("scenarios.slug"))
    seeds: Mapped[str] = mapped_column(Text)                      # JSON list of ints
    results_yaml: Mapped[str] = mapped_column(Text)
    results_csv: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
```

---

## API additions (`api/app.py`)

New router: `/scenarios`

| Method | Route | Body | Returns |
|--------|-------|------|---------|
| `GET` | `/scenarios` |: | `list[ScenarioSummary]` |
| `POST` | `/scenarios` | `ScenarioCreate(slug, name, yaml_content)` | `ScenarioRecord` |
| `GET` | `/scenarios/{slug}` |: | `ScenarioDetail` (includes parsed Pydantic model) |
| `DELETE` | `/scenarios/{slug}` |: | `204` |
| `POST` | `/scenarios/import` | multipart CSV file | `ScenarioRecord` |
| `POST` | `/scenarios/compare` | `CompareRequest(slugs: list[str], n_reps)` | `list[EvaluationResult]` |

`/simulate`, `/optimize`, `/export` gain an optional `scenario_slug` param.
Default: `"whisker-haven"` (seeded on startup from `scenarios/whisker_haven.yaml`).

---

## CSV ingestion (`POST /scenarios/import`)

Accepts a CSV export from Shelterluv or PetPoint. Required columns:

| CSV column | Maps to Scenario field |
|-----------|----------------------|
| `intake_date` | Used to compute `intake_rate_per_day` (Poisson λ) |
| `animal_type` | Filter to cats only |
| `intake_reason` | `stray` → standard flow; `owner_surrender` → skip assessment |
| `outcome_type` | `adoption` / `transfer` / `euthanasia` |
| `los_days` | Length of stay → validates model calibration |
| `medical_flag` | Fraction → `isolation_fraction` |

Ingestion produces a `Scenario` Pydantic model, serializes to YAML, stores in DB.

---

## UI additions

- Step 1 gains a scenario **select dropdown** (loads `GET /scenarios`)
- A **"Upload YAML"** button opens a file picker → `POST /scenarios`
- A **"Import CSV"** button → `POST /scenarios/import`
- Step 5 (Compare) gains a **"vs another scenario"** mode that shows two scenario columns

---

## Storage location

Default: `shelter_pulse.db` in the project root (gitignored).
Configurable via `SHELTER_PULSE_DB_URL` env var (SQLAlchemy connection string).
Phase 5 migrates to PostgreSQL via Alembic; the ORM layer is unchanged.

---

## Seeding

On API startup, if the `whisker-haven` scenario does not exist in the DB, seed it from
`scenarios/whisker_haven.yaml`. This ensures the demo always works without manual setup.
