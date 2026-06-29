# Worker: UI

**Model:** Claude Sonnet 4.6 | **Effort:** medium-high | **Phase:** 8, 10

**Role:** Maintain and extend `ui/`. Next.js app router, TypeScript strict, Tailwind CSS.

## MANDATORY: Read `ui/AGENTS.md` before writing any Next.js code.

## Files You Own

Everything under `ui/src/`. Reference `ui/AGENTS.md` but do not edit it.

Forbidden zones: shelterpulse/ (Python), .github/workflows/, .kiro/steering/

## Current Structure

```
ui/src/app/
├── [lang]/
│   ├── page.tsx            (root landing page)
│   ├── layout.tsx
│   ├── demo/
│   │   ├── DemoClient.tsx  (client component)
│   │   └── page.tsx        (server page)
│   ├── how-it-works/
│   │   ├── HowItWorksClient.tsx
│   │   └── page.tsx
│   └── simulate/
│       ├── SimulateClient.tsx
│       └── page.tsx
├── layout.tsx              (root layout, redirects to /en)
└── page.tsx
```

All user-facing pages are under `[lang]/` for i18n routing. Only `en` is active.

## Rules

- No new npm packages without Orchestrator approval. Check `package.json` first.
- TypeScript strict mode. No `any` without inline justification comment.
- API base URL: `process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"`
- CSS bar charts via Tailwind `width-[X%]` divs -- no chart library needed
- Domain language: cats, kittens, isolation queue, foster placement, vet tech (never "entities")
- `"use client"` directive only on components that need browser APIs or event handlers
- Page files (page.tsx) are server components; all state/effects go in *Client.tsx

## How to Test

```bash
cd ui
npm run build     # TypeScript check + Next.js static export -- must pass
npm run dev       # dev server at :3000 -- verify pages render correctly
```

## Phase 8 Task (Issue #36)

Add BO-vs-baselines comparison panel to `ui/src/app/[lang]/simulate/SimulateClient.tsx`.

The `/optimize` API returns `list[EvaluationResult]` with `allocation_name`, `mean_overflow`,
`total_cost`, and feasibility flag. Display as a ranked table with:
- Named baselines labeled (e.g., "Equal Split", "All Foster", "Domain Heuristic")
- BO winner highlighted
- Tailwind table styling (no new npm packages)

## Phase 10 Tasks

**Issue #50 ("What if" sliders):**
Add sliders to `SimulateClient.tsx` for intake rate multiplier and housing capacity.
On change: re-run `/simulate` and update timeline chart. Debounce calls (300ms).

**Issue #51 (Accessibility):**
- Run axe-core in browser dev tools on all pages
- Fix contrast ratio failures (WCAG AA minimum)
- Verify all interactive elements have keyboard focus + visible focus ring
- Verify tab order is logical on the wizard

## API Response Shape (for TypeScript types)

```typescript
interface EvaluationResult {
  allocation_name: string;          // "equal_split", "bo_candidate_0", etc.
  allocation: Record<string, number>; // shares summing to 1
  mean_overflow: number;
  std_overflow: number;
  total_cost: number;
  feasible: boolean;
  ci_95: [number, number];
}
```
