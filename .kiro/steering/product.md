---
inclusion: always
---

# ShelterPulse: Product Overview

**What this is:** A simulation and optimization laboratory for cat-shelter resource allocation, originally built for the #hackthekitty 2026 hackathon and continuing as an ongoing project.

**Core demo scenario:** "Whisker Haven": a mid-size cat-only rescue shelter navigating kitten season (spring/summer intake surge). The shelter has 35 housing slots, 5 isolation slots, 1.5 FTE vet techs, a small foster network (8 placements), and a $5,000 intervention budget. Intake surges 2.5x during kitten season peak. The model runs a 90-day simulation covering the full cat flow: intake → assessment → isolation/medical clearance → housing → foster → adoption-ready → adopted/transferred.

**Custom simulation:** Beyond the demo, any user can build their own scenario: choosing geographic area (urban/suburban/rural), climate region, shelter size, budget, and personal constraints. The system simulates and optimizes against their specific parameters.

**What it solves:** Given a fixed intervention budget, how should a shelter allocate it across four strategies (foster support, extra clinic hours, temporary isolation expansion, adoption events) to minimize "overflow cat-days": cat-days spent above housing capacity during kitten season?

**Primary users:**
- Shelter managers: configure custom scenarios, review optimization + analytics
- Developers extending the project: access the live URL or run `docker compose up`, explore via UI + API + CLI

**Language throughout:** Speak in cats, not "entities" or "units." Kitten season, isolation queue, foster placement, adoption counselor: these are the domain terms. Keep them concrete and visible everywhere.
