# ShelterPulse Demo Script

**Total time:** < 5 minutes

---

## Beat 1: The Problem (0:00–0:40)

**[Show landing page at /en]**

> "Every spring, kitten season overwhelms cat shelters across the country. Intake surges 2–3x, isolation queues back up, and shelter managers have to make tough resource decisions with limited budgets."

> "ShelterPulse lets you simulate your shelter under uncertainty — and find the best way to spend your intervention budget before a single cat is at risk."

**[Point to the three feature cards: Simulation, Optimization, Custom Scenarios]**

---

## Beat 2: Whisker Haven Demo (0:40–1:40)

**[Click "Try the Demo"]**

> "Let's see a pre-configured example. Whisker Haven is a mid-size cat rescue with 35 housing slots, 5 isolation slots, and a $5,000 intervention budget."

**[Step through the 6-step wizard]**

> "Step 1 shows the scenario config. Step 2 runs a baseline — with no interventions, we see over 200 overflow cat-days during kitten season."

> "Step 3 shows the bottlenecks — isolation is the chokepoint. Step 4 runs Bayesian Optimization and finds the best allocation."

> "The optimizer reduces overflow to zero by investing heavily in adoption events and foster support. Step 5 compares all strategies head-to-head, and Step 6 lets you export everything."

---

## Beat 3: Custom Simulation (1:40–3:00)

**[Navigate to /en/simulate]**

> "Now let's build YOUR shelter. I'll set up a larger urban facility — 120 housing slots, 20 isolation, higher intake of 5 cats/day."

**[Fill in custom parameters]**

> "I'll keep the $5,000 budget constraint. Let's simulate."

**[Click Simulate]**

> "We get the overflow result with a 95% confidence interval — showing uncertainty across Monte Carlo replications."

---

## Beat 4: Analytics (3:00–3:40)

**[Click Timeline tab]**

> "The timeline shows day-by-day housing usage. You can see the surge hitting around day 15 and peaking around day 40. Red bars mean overflow."

**[Click Sensitivity tab]**

> "Sensitivity analysis tells us which parameters matter most. Intake rate has the biggest impact on overflow — a 20% increase nearly doubles it."

---

## Beat 5: Optimization (3:40–4:20)

**[Click Optimize]**

> "Now let's optimize. The system evaluates dozens of budget allocations using Gaussian Process surrogate + Expected Improvement acquisition."

**[Show results]**

> "Best allocation: 40% to adoption events, 35% to foster support, 15% to temporary isolation, 10% to clinic hours. Overflow drops from 150 to 12 cat-days."

---

## Beat 6: Technical Highlights (4:20–4:50)

**[Show /docs API endpoint]**

> "Everything is API-first. Full REST API with OpenAPI docs."

> "The architecture is Temporal-ready for production scaling. Docker Compose gets you running in one command. Supports 4 languages. All code open-source under Apache-2.0."

**[Show terminal: `docker compose up`]**

> "One command. That's it."

---

## Key talking points (if asked)

- **Simulation engine:** SimPy discrete-event, non-homogeneous Poisson intake, realistic cat lifecycle
- **Optimizer:** GP surrogate + EI acquisition (scipy fallback), common random numbers for fair comparison
- **Analytics:** Sensitivity analysis, time-series visualization, CI-95 uncertainty bands
- **Frontend:** Next.js 16 static export, 4 languages (en/es/fr/pt), Tailwind CSS, zero chart dependencies
- **Infrastructure:** Docker multi-stage, nginx for static files, precomputed cache for instant demo
