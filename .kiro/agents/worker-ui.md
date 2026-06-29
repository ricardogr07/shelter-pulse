# Worker: UI: Next.js 6-Step Wizard

**Model:** Claude Sonnet 4.6 | **Effort:** high  
**Depends on:** API worker must be DONE  
**Target:** Jul 4-5 (Phase 3)

## Role

Replace the placeholder `ui/src/app/page.tsx` with a single-page 6-step wizard that calls the FastAPI backend. Steps: Configure → Baseline → Bottleneck → Optimize → Compare → Export.

## Read first

```
@.localagent/agents/SHARED.md
@.localagent/docs/08-ui-flows.md
```

**CRITICAL: Before writing any Next.js code, read `ui/AGENTS.md`.** This version has breaking changes. Then check `node_modules/next/dist/docs/` for the real API docs.

## Files you own

| File | Action |
|------|--------|
| `ui/src/app/page.tsx` | **Replace** (currently a placeholder) |
| `ui/src/types.ts` | **Create** |
| `ui/src/api.ts` | **Create** |
| `ui/.env.local` | **Create** if missing |
| `ui/.env.production` | **Create** if missing |

## Files you must NOT touch

- `ui/next.config.ts`: only modify if `output: "standalone"` is needed and not set
- `ui/package.json`: no new packages without approval
- All Python files
- `.github/workflows/`

## Done criteria

- [ ] `cd ui && npm run dev` starts without errors
- [ ] Step 1 → 2 → 3 navigates without API (steps 1 and 3 are static content)
- [ ] Step 4 calls `/optimize` and displays results when API is running
- [ ] Step 5 shows comparison table (4 named baselines + BO winner)
- [ ] Step 6 triggers ZIP download
- [ ] `cd ui && npm run build` succeeds (static export check)
- [ ] Update `.localagent/docs/STATUS.md` row for UI

## Key rules

- **Single page** at `/`: all 6 steps as conditional sections, wizard state in `useState`
- **No new npm packages**: check `ui/package.json` before reaching for a chart lib
- If no chart lib is installed: use CSS bar chart (Tailwind width % via inline style)
- TypeScript strict mode is on: no `any` without justification
- Cat-shelter language throughout: never say "entity", "unit", "agent"
- `NEXT_PUBLIC_API_URL` env var (default `http://localhost:8000`)
- Show sensible error state when API is down: don't crash

## Environment setup

`ui/.env.local`:
```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

`ui/.env.production`:
```
NEXT_PUBLIC_API_URL=https://shelterpulse-api.onrender.com
```
(update production URL after cloud deployment)
