---
inclusion: always
---

# ShelterPulse: Product Overview

**What this is:** A simulation and optimization laboratory for cat-shelter resource allocation, built for the #hackthekitty 2026 hackathon.

**Core demo scenario:** "Whisker Haven": a mid-size cat-only rescue shelter navigating kitten season (spring/summer intake surge). The shelter has 80 housing slots, 12 isolation slots, 1.5 FTE vet techs, and a $5,000 intervention budget. The model runs a 90-day simulation covering the full cat flow: intake → assessment → isolation/medical clearance → housing → foster → adoption-ready → adopted/transferred.

**Custom simulation:** Beyond the demo, any user can build their own scenario: choosing geographic area (urban/suburban/rural), climate region, shelter size, budget, and personal constraints. The system simulates and optimizes against their specific parameters.

**What it solves:** Given a fixed intervention budget, how should a shelter allocate it across four strategies (foster support, extra clinic hours, temporary isolation expansion, adoption events) to minimize "overflow cat-days": cat-days spent above housing capacity during kitten season?

**Primary users:**
- Shelter managers: configure custom scenarios, review optimization + analytics
- Hackathon judges: access live URL or run `docker compose up`, evaluate via UI + API + CLI

**Deadline:** Submit by Jul 6 2026 (hard deadline Jul 7 23:59 BST).

**Phases (ALL ship by Jul 7):**
1. Core sim + API + CLI + wizard + Docker (DONE)
2. UI expansion: landing page, routing, custom simulation builder
3. Analytics: sensitivity analysis, time-series, uncertainty bands
4. Polish: security scan, demo script, UX refinements, Temporal gate
5. Cloud (AWS App Runner) + demo video + submission

**Non-negotiables (never cut):**
1. < 5 min demo video covering landing page + custom simulation + optimization
2. README a stranger can run from
3. Aikido/pip-audit scan report in `/security/`
4. `.kiro/` folder committed
5. Honest baseline comparison for the optimizer
6. Custom simulation page with geographic + constraint inputs

**Language throughout:** Speak in cats, not "entities" or "units." Kitten season, isolation queue, foster placement, adoption counselor: these are the domain terms. Keep them concrete and visible everywhere.
