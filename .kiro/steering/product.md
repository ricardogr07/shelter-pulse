---
inclusion: always
---

# ShelterPulse: Product Overview

**What this is:** A simulation and optimization laboratory for cat-shelter resource allocation, built for the #hackthekitty 2026 hackathon.

**Core demo scenario:** "Whisker Haven": a mid-size cat-only rescue shelter navigating kitten season (spring/summer intake surge). The shelter has 35 housing slots, 5 isolation slots, 1.5 FTE vet techs, a small foster network (8 placements), and a $5,000 intervention budget. Intake surges 2.5x during kitten season peak. The model runs a 90-day simulation covering the full cat flow: intake → assessment → isolation/medical clearance → housing → foster → adoption-ready → adopted/transferred.

**Custom simulation:** Beyond the demo, any user can build their own scenario: choosing geographic area (urban/suburban/rural), climate region, shelter size, budget, and personal constraints. The system simulates and optimizes against their specific parameters.

**What it solves:** Given a fixed intervention budget, how should a shelter allocate it across four strategies (foster support, extra clinic hours, temporary isolation expansion, adoption events) to minimize "overflow cat-days": cat-days spent above housing capacity during kitten season?

**Primary users:**
- Shelter managers: configure custom scenarios, review optimization + analytics
- Hackathon judges: access live URL or run `docker compose up`, evaluate via UI + API + CLI

**Deadline:** Submit by Jul 6 2026 (hard deadline Jul 6 23:59 BST). No extensions.

**Phase status (Jun 29 2026):**

Phases 1-11 code is **COMPLETE**. All Python files, UI pages, Docker config, and Terraform
infrastructure exist and are deployed. Remaining work is submission sprint (Phases 6-11).

| Phase | Name | Status |
|-------|------|--------|
| 1-5 | Core sim, BO, API, CLI, UI, Docker, ECS deploy | DONE |
| 6 | Aikido Security Scan | TODO |
| 7 | AWS Deployment (verify live) | TODO |
| 8 | Polish and Rubric improvements | TODO |
| 9 | Async BO workers + Observability | TODO |
| 10 | Pre-deliverable ideas backlog | TODO |
| 11 | Final Deliverable: video + submission | TODO |

GitHub Project #5 tracks all remaining work: https://github.com/users/ricardogr07/projects/5

**Non-negotiables (never cut):**
1. < 5 min demo video covering landing page + custom simulation + optimization
2. README a stranger can run from
3. Aikido/pip-audit scan report in `/security/`
4. `.kiro/` folder committed
5. Honest baseline comparison for the optimizer
6. Custom simulation page with geographic + constraint inputs

**Language throughout:** Speak in cats, not "entities" or "units." Kitten season, isolation queue, foster placement, adoption counselor: these are the domain terms. Keep them concrete and visible everywhere.
