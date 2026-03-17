---
phase: 04-trading-terminal-frontend
plan: 01
subsystem: ui
tags: [nextjs, tailwind-v4, zustand, lightweight-charts, sse, typescript, vitest]

requires:
  - phase: 03-llm-chat-integration
    provides: All backend API endpoints (portfolio, watchlist, chat, SSE streaming)
provides:
  - Next.js 15 project with static export and Tailwind v4 dark theme
  - TypeScript interfaces matching all backend API contracts
  - Zustand stores for price, portfolio, chat, watchlist state
  - SSE hook for EventSource connection to /api/stream/prices
  - Lightweight Charts hook with dark theme and ResizeObserver
  - API client with fetch wrappers for all endpoints
  - Header component with portfolio value, cash, and connection dot
  - Terminal grid layout with placeholder panels
  - Vitest + React Testing Library test infrastructure
affects: [04-02, 04-03, 04-04, 04-05]

tech-stack:
  added: [next@15.5.13, react@19.1.0, tailwindcss@4, zustand@5, lightweight-charts@4.2.3, d3-hierarchy@3.1.2, vitest@4.1.0]
  patterns: [zustand-selectors, eventsource-hook, css-first-tailwind-theme, resizeobserver-chart-hook]

key-files:
  created:
    - frontend/package.json
    - frontend/next.config.ts
    - frontend/src/app/globals.css
    - frontend/src/app/layout.tsx
    - frontend/src/app/page.tsx
    - frontend/src/types/index.ts
    - frontend/src/lib/api.ts
    - frontend/src/stores/priceStore.ts
    - frontend/src/stores/portfolioStore.ts
    - frontend/src/stores/chatStore.ts
    - frontend/src/stores/watchlistStore.ts
    - frontend/src/hooks/useSSE.ts
    - frontend/src/hooks/useLightweightChart.ts
    - frontend/src/components/Header.tsx
    - frontend/src/components/ConnectionDot.tsx
    - frontend/vitest.config.ts
    - frontend/src/test-utils.tsx
  modified:
    - .gitignore

key-decisions:
  - "Used addLineSeries() API (LW Charts v4.2.3) instead of addSeries(LineSeries) pattern from research"
  - "Fixed root .gitignore lib/ pattern to /lib/ to avoid blocking frontend/src/lib/"
  - "create-next-app@15.5 ships React 19 and Tailwind v4 natively, no manual upgrade needed"

patterns-established:
  - "Zustand selectors: components subscribe to specific state slices to minimize re-renders"
  - "SSE hook: single useSSE() call at page level feeds price store"
  - "API client: thin fetch wrappers in src/lib/api.ts, all same-origin"
  - "CSS-first Tailwind v4: custom theme via @theme directive in globals.css"

requirements-completed: [UI-01, UI-12]

duration: 7min
completed: 2026-03-17
---

# Phase 4 Plan 1: Frontend Scaffold Summary

**Next.js 15 static export with Tailwind v4 dark terminal theme, Zustand stores, SSE/chart hooks, Header component, and Vitest test infrastructure**

## Performance

- **Duration:** 7 min
- **Started:** 2026-03-17T07:13:40Z
- **Completed:** 2026-03-17T07:20:28Z
- **Tasks:** 3
- **Files modified:** 18

## Accomplishments
- Next.js 15.5 project with static export producing out/ directory
- Complete Tailwind v4 dark terminal theme with all project colors
- Four Zustand stores (price, portfolio, chat, watchlist) with async actions
- SSE hook, Lightweight Charts hook, API client covering all backend endpoints
- Header with live portfolio value, cash balance, and connection status dot
- Vitest + React Testing Library configured and verified

## Task Commits

Each task was committed atomically:

1. **Task 1: Scaffold Next.js 15, install deps, configure Tailwind v4 and static export** - `2212e08` (feat)
2. **Task 2: Create types, API client, and Zustand stores** - `a01f382` (feat)
3. **Task 3: Create hooks, Header, ConnectionDot, page layout, and Vitest test infrastructure** - `3b4b49a` (feat)

## Files Created/Modified
- `frontend/package.json` - Next.js 15 project with all dependencies
- `frontend/next.config.ts` - Static export configuration
- `frontend/postcss.config.mjs` - Tailwind v4 PostCSS plugin
- `frontend/src/app/globals.css` - Tailwind v4 theme with terminal colors and price flash classes
- `frontend/src/app/layout.tsx` - Root layout with dark theme
- `frontend/src/app/page.tsx` - Terminal grid layout with Header and placeholder panels
- `frontend/src/types/index.ts` - TypeScript interfaces for all API contracts
- `frontend/src/lib/api.ts` - Fetch wrappers for all backend endpoints
- `frontend/src/stores/priceStore.ts` - Price state with SSE integration and capped history
- `frontend/src/stores/portfolioStore.ts` - Portfolio state with fetch and trade actions
- `frontend/src/stores/chatStore.ts` - Chat state with message history
- `frontend/src/stores/watchlistStore.ts` - Watchlist state with CRUD actions
- `frontend/src/hooks/useSSE.ts` - EventSource connection manager
- `frontend/src/hooks/useLightweightChart.ts` - Chart lifecycle with ResizeObserver
- `frontend/src/components/Header.tsx` - Portfolio value, cash, connection dot
- `frontend/src/components/ConnectionDot.tsx` - Green/yellow/red status indicator
- `frontend/vitest.config.ts` - Vitest with jsdom and path alias
- `frontend/src/test-utils.tsx` - Custom render wrapper
- `.gitignore` - Fixed lib/ pattern to /lib/

## Decisions Made
- Used `addLineSeries()` API for Lightweight Charts v4.2.3 (research incorrectly suggested `addSeries(LineSeries)` pattern which is v5)
- Fixed root `.gitignore` `lib/` pattern to `/lib/` so it only matches the root lib directory, not `frontend/src/lib/`
- Kept React 19 as scaffolded by create-next-app@15.5 (research suggested React 18 but v15.5 ships v19 natively)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed Lightweight Charts API for v4.2.3**
- **Found during:** Task 3 (useLightweightChart hook)
- **Issue:** Research pattern used `chart.addSeries(LineSeries)` which is a v5 API; v4.2.3 uses `chart.addLineSeries()`
- **Fix:** Changed to `chart.addLineSeries()` and removed `LineSeries` import
- **Files modified:** frontend/src/hooks/useLightweightChart.ts
- **Verification:** Build passes
- **Committed in:** 3b4b49a (Task 3 commit)

**2. [Rule 3 - Blocking] Fixed .gitignore blocking frontend/src/lib/**
- **Found during:** Task 2 (API client creation)
- **Issue:** Root `.gitignore` had `lib/` pattern which matched `frontend/src/lib/` preventing git add
- **Fix:** Changed `lib/` to `/lib/` (root-only match)
- **Files modified:** .gitignore
- **Verification:** git add succeeds for frontend/src/lib/api.ts
- **Committed in:** a01f382 (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (1 bug, 1 blocking)
**Impact on plan:** Both fixes necessary for correctness. No scope creep.

## Issues Encountered
None beyond the auto-fixed deviations above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All stores, hooks, types, and API client ready for component development
- Placeholder panels in grid layout ready to be replaced with real components
- Vitest infrastructure ready for component tests
- Build verified with static export

## Self-Check: PASSED

All 17 files verified present. All 3 task commits verified in git log.

---
*Phase: 04-trading-terminal-frontend*
*Completed: 2026-03-17*
