# Built with Kiro

ShelterPulse was developed with help from [Kiro](https://kiro.dev), an AI-powered development environment. Kiro served as pair programmer across different phases — from architecture integration into AWS through production deployment — while I made all design decisions and validated every output.

## Development phases

### Phase 1–2: Core simulation engine

Kiro assisted with:
- Designing the SimPy discrete-event architecture (intake → isolation → housing → adoption lifecycle)
- Implementing the non-homogeneous Poisson intake process with seasonal spikes
- Writing the `CandidateAllocation` dataclass and intervention resolution logic
- Establishing the `shelterpulse/core/` boundary invariant (no I/O imports)

### Phase 3: Optimization layer

- Implementing Common Random Numbers (CRN) for variance reduction
- Writing the GP+EI Bayesian Optimization loop, which was later introduced with jaxbo
- Defining the baselines and the evaluation interface based on the simulation engine I proposed

### Phase 4: API + frontend

- Structuring the FastAPI REST adapter with Pydantic models
- Building the Next.js 16 + TypeScript + Tailwind frontend boilerplate
- Creating the 6-step demo wizard and custom builder form boilerplate
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

- Writing the multi-stage Dockerfile (nginx + uvicorn in one container) for local testing
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
| Documentation | ADRs, README, design decisions|

## What worked well

1. **Rapid iteration** — Changes that would take 30–60 minutes to write manually were produced in seconds and verified against the test suite immediately.
2. **Cross-stack coherence** — Kiro maintained context across Python backend, TypeScript frontend, Docker config, and CI workflows in the same session.
3. **Test-first approach** — Writing tests alongside implementation exposed scientific-contract defects in overflow units, foster capacity, random-stream alignment, and optimizer result labeling.
4. **Infrastructure debugging** — Multi-step deployment issues (ECS rolling update, nginx proxy, port mapping) were diagnosed systematically rather than through trial-and-error.

## What required human judgment

- **Domain modeling** — How to distinguish modeled queue effects from claims requiring real-shelter calibration
- **UX decisions** — Step ordering in the demo wizard, which metrics to surface prominently
- **Architecture choices** — Consolidated container vs. microservices, Temporal deferral decision
- **Prioritization** — Rubric weighting drove task ordering (Innovation 20% items first)
- **Validation** — Stale `234 → 0` and sub-30-second claims were removed after the corrected 20×32 evidence run did not reproduce them

## Verification approach

Every AI-generated change was validated through:
1. **Local tests** — `pytest` (unit + e2e) and `npx cypress run` before every commit
2. **CI pipeline** — GitHub Actions runs lint, security, tests, type-check, and Docker build on every PR
3. **Build verification** — `npm run build` confirms static export succeeds (catches missing pages, bad imports)
4. **Live verification** — After deployment, curl against the live URL to confirm API 200 and UI 200, run smoke tests, and e2e tests against the live site
5. **Manual review** — HTML output inspected for correct metadata, SEO tags, and redirect behavior, and a general correctness review of the UI and API responses
