# ShelterPulse whitepaper

This directory contains the development technical report and its machine-readable case-study evidence.

## Evidence first

Generate the Whisker Haven evidence before changing quantitative claims:

```powershell
uv run --extra optimize python scripts/generate_whitepaper_evidence.py `
  --candidates 20 `
  --replications 32 `
  --output docs/whitepaper/evidence/whisker-haven.json
```

The JSON records configuration, seeds, environment, source digests, complete ranking, confidence intervals, and timing. Regenerate it after any model, optimizer, scenario, or dependency change and on the final release commit.

## Build the PDF

Prerequisites:

- Pandoc 3+
- a LaTeX distribution providing `pdflatex`
- the repository development environment (`uv sync --dev`)

Canonical command:

```powershell
uv run tox -e whitepaper
```

Direct equivalent:

```powershell
Push-Location docs/whitepaper
pandoc whitepaper.md --citeproc --bibliography=references.bib --csl=ieee.csl --pdf-engine=pdflatex -V geometry:margin=1in -V fontsize=11pt -V classoption=twocolumn -o shelterpulse-whitepaper.pdf
Pop-Location
```

The `Whitepaper` GitHub Actions workflow runs the tox environment on relevant pull requests and pushes. It validates the build but does not commit or push generated files.

## Files

| File | Purpose |
|---|---|
| `whitepaper.md` | Report source |
| `references.bib` | Verified bibliography metadata |
| `ieee.csl` | Citation style |
| `evidence/whisker-haven.json` | Generated case-study evidence |
| `shelterpulse-whitepaper.pdf` | Generated report output |

## Review checklist

- Every numeric claim is present in an evidence artifact or cited source.
- The paper distinguishes intervention spend from simulated operating cost.
- Baseline winners are not labeled Bayesian-optimization winners.
- Runtime is presented as environment-specific unless repeated final-commit runs support a threshold.
- The revision statement matches the final submitted commit or tag.
- `rg -n "TODO|TBD|v1.0.0|234|under 30" docs/whitepaper` returns no stale publication claim.
