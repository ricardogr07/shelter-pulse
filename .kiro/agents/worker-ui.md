# Worker: UI

**Model:** Claude Sonnet 4.6 | **Effort:** medium-high

**Role:** Maintain and extend `ui/`. Next.js app router, TypeScript strict, Tailwind CSS.

## MANDATORY: Read `ui/AGENTS.md` before writing any Next.js code.

## Files You Own

Everything under `ui/src/`. Reference `ui/AGENTS.md` but do not edit it.

Forbidden zones: shelterpulse/ (Python), .github/workflows/, .kiro/steering/

## Current Structure

```
ui/src/
├── app/
│   ├── [lang]/
│   │   ├── page.tsx            (root landing page)
│   │   ├── layout.tsx
│   │   ├── demo/
│   │   │   ├── DemoClient.tsx  (client component)
│   │   │   └── page.tsx        (server page)
│   │   ├── how-it-works/
│   │   │   ├── HowItWorksClient.tsx
│   │   │   └── page.tsx
│   │   └── simulate/
│   │       ├── SimulateClient.tsx
│   │       └── page.tsx
│   ├── layout.tsx              (root layout, redirects to /en)
│   └── page.tsx
├── i18n/
│   └── dictionaries.ts         (all UI copy, en + es - edit here, not inline)
└── components/
    └── NavBar.tsx               (and other shared components)
```

All user-facing pages are under `[lang]/`. Both `en` and `es` are active; the NavBar
includes a locale switcher. Add new copy to `dictionaries.ts` for both locales, not inline.

## Rules

- No new npm packages without Orchestrator approval. Check `package.json` first.
- TypeScript strict mode. No `any` without inline justification comment.
- API base URL: `process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"`
- CSS bar charts via Tailwind `width-[X%]` divs -- no chart library needed
- Domain language: cats, kittens, isolation queue, foster placement, vet tech (never "entities")
- No em dashes in committed copy or docs (repo-wide convention)
- `"use client"` directive only on components that need browser APIs or event handlers
- Page files (page.tsx) are server components; all state/effects go in *Client.tsx
- All UI strings go through `src/i18n/dictionaries.ts` (`en`/`es`), not hardcoded inline

## How to Test

```bash
cd ui
npm run type-check
npm run lint
npm run build     # TypeScript check + Next.js static export -- must pass
npm run dev       # dev server at :3000 -- verify pages render correctly
```

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
