# ShelterPulse UI

Next.js (App Router) + React + TypeScript + Tailwind CSS frontend for
ShelterPulse. A thin adapter over the FastAPI backend; no business logic
lives here (see the root [README](../README.md) and
[`docs/architecture/`](../docs/architecture/) for the full system).

## Pages

- `/[lang]` - landing page (`en`/`es`)
- `/[lang]/demo` - guided Whisker Haven walkthrough: baseline, bottleneck
  analysis, optimize, compare
- `/[lang]/how-it-works` - the model explained end to end (intake through
  optimization), with a "Download Whitepaper (PDF)" button linking to
  `public/shelterpulse-whitepaper.pdf`
- `/[lang]/simulate` - custom scenario builder and run history
- `/[lang]/legal/privacy` - privacy policy

## Getting started

```bash
npm ci
npm run dev
```

Open [http://localhost:3000](http://localhost:3000). Requires the API
running separately (`docker compose up` from the repo root is the easiest
way to get API + RabbitMQ + worker running alongside this UI - see the root
README's reproducibility steps).

## Commands

```bash
npm run build        # production build (static export, served by nginx in the deployed image)
npm run type-check    # tsc --noEmit
npm run lint          # eslint
npm run cy:run         # Cypress e2e (headless)
npm run cy:open        # Cypress e2e (interactive)
```

## i18n

Locale strings live in `src/i18n/dictionaries.ts` (`en`/`es`). Add new UI
copy there, not inline, so both locales stay in sync.
