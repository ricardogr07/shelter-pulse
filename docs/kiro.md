# Built with Kiro

ShelterPulse was developed entirely with [Kiro](https://kiro.dev), an AI-powered development environment. Kiro served as pair programmer across every phase — from architecture design through production deployment — while the human developer made all design decisions and validated every output.

## Development phases

### Phase 1–2: Core simulation engine

Kiro assisted with:
- Designing the SimPy discrete-event architecture (intake → isolation → housing → adoption lifecycle)
- Implementing the non-homogeneous Poisson intake process with seasonal spikes
- Writing the `CandidateAllocation` dataclass and intervention resolution logic
- Establishing the `shelterpulse/core/` boundary invariant (no I/O imports)

### Phase 3: Optimization layer

- Implementing Common Random Numbers (CRN) for variance reduction
- Writing the GP+EI Bayesian Optimization loop using jaxbo
- Adding scipy fallback for environments without JAX
- Defining the 5 named baselines and the evaluation interface

### Phase 4: API + frontend

- Structuring the FastAPI REST adapter with Pydantic models
- Building the Next.js 15 + TypeScript + Tailwind frontend
- Creating the 6-step demo wizard and custom builder form
- Implementing zero-dependency charts (Tailwind `width: X%` bars)

### Phase 5: CI/CD pipeline

- Setting up tox with lint, security, test, and e2e environments
- Writing GitHub Actions CI with path-based job filtering
- Adding Cypress smoke tests for the static export
- Configuring pyrefly + bandit for Python, ESLint + tsc for TypeScript

### Phase 6: Security

- Fixing all 8 Aikido security findings (SSRF, header injection, path traversal, etc.)
- Auditing dependencies for known vulnerabilities
- Adding input validation throughout the API layer

### Phase 7: Infrastructure

- Writing the multi-stage Dockerfile (nginx + uvicorn in one container)
- Configuring ECS Fargate Express Mode deployment
- Setting up the release workflow (v* tag → ECR push → ECS deploy)
- Debugging the rolling deployment (container port change, ALB health checks)

### Phase 8: Polish

- SEO optimization (OpenGraph, Twitter cards, hreflang, robots.txt, sitemap.xml, llms.txt)
- BO-vs-baselines comparison panel with shared component
- Timeline before/after overlay visualization
- Test coverage improvements (warm-start test, timeline tests)

## Types of work

| Category | Examples |
|----------|----------|
| Architecture | Module boundaries, ADR writing, data flow design |
| Code generation | Engine, optimizer, API endpoints, React components |
| Test writing | pytest unit/e2e, Cypress smoke tests |
| Debugging | SimPy race conditions, ECS deployment issues, CI failures |
| Infrastructure | Dockerfile, nginx.conf, GitHub Actions, AWS CLI |
| Security | Aikido finding remediation, input validation |
| Documentation | ADRs, README, design decisions, this write-up |

## What worked well

1. **Rapid iteration** — Changes that would take 30–60 minutes to write manually were produced in seconds and verified against the test suite immediately.
2. **Cross-stack coherence** — Kiro maintained context across Python backend, TypeScript frontend, Docker config, and CI workflows in the same session.
3. **Test-first approach** — Writing tests alongside implementation caught regressions immediately (e.g., the warm-start test revealed the optimizer returns warm-start + new results, not just n_candidates).
4. **Infrastructure debugging** — Multi-step deployment issues (ECS rolling update, nginx proxy, port mapping) were diagnosed systematically rather than through trial-and-error.

## What required human judgment

- **Domain modeling** — Whether clinic hours should be excluded from the domain heuristic (it worsened overflow in testing)
- **UX decisions** — Step ordering in the demo wizard, which metrics to surface prominently
- **Architecture choices** — Consolidated container vs. microservices, Temporal deferral decision
- **Prioritization** — Rubric weighting drove task ordering (Innovation 20% items first)
- **Validation** — Every claim about "overflow reduced to 0" was verified by actually running the simulation

## Verification approach

Every AI-generated change was validated through:
1. **Local tests** — `pytest` (unit + e2e) and `npx cypress run` before every commit
2. **CI pipeline** — GitHub Actions runs lint, security, tests, type-check, and Docker build on every PR
3. **Build verification** — `npm run build` confirms static export succeeds (catches missing pages, bad imports)
4. **Live verification** — After deployment, curl against the live URL to confirm API 200 and UI 200
5. **Manual review** — HTML output inspected for correct metadata, SEO tags, and redirect behavior
