---
phase: 04-trading-terminal-frontend
plan: 02
subsystem: ui
tags: [react, zustand, lightweight-charts, sse, tailwind, vitest]

requires:
  - phase: 04-trading-terminal-frontend-01
    provides: "Next.js project, Zustand stores (priceStore, watchlistStore), useLightweightChart hook, SSE connection, CSS flash classes"
provides:
  - "Watchlist component with live prices, flash animations, sparklines"
  - "MainChart component with area chart for selected ticker"
  - "Page layout with selectedTicker state wiring Watchlist to MainChart"
affects: [04-trading-terminal-frontend-03, 04-trading-terminal-frontend-04]

tech-stack:
  added: []
  patterns: ["Per-ticker Zustand selectors for minimal re-rendering", "SVG polyline sparklines for lightweight mini-charts", "TDD with vitest and testing-library"]

key-files:
  created:
    - frontend/src/components/Watchlist.tsx
    - frontend/src/components/MainChart.tsx
    - frontend/src/__tests__/Watchlist.test.tsx
    - frontend/src/__tests__/MainChart.test.tsx
    - frontend/src/setupTests.ts
  modified:
    - frontend/src/app/page.tsx
    - frontend/vitest.config.ts
    - frontend/src/components/PortfolioHeatmap.tsx

key-decisions:
  - "SVG polyline sparklines instead of Lightweight Charts for mini-charts (simpler at 100x30px size)"
  - "addAreaSeries() for LW Charts v4.2.3 (not addSeries(AreaSeries) from newer API)"
  - "Time type cast required for LW Charts setData compatibility"

patterns-established:
  - "Per-ticker Zustand selector: usePriceStore(s => s.prices[ticker]) for optimal re-rendering"
  - "Price flash via useState + useEffect keyed on price value, 500ms timeout to clear"

requirements-completed: [UI-02, UI-03, UI-04, UI-05]

duration: 6min
completed: 2026-03-17
---

# Phase 4 Plan 2: Watchlist & MainChart Summary

**Watchlist panel with live price flash animations, SVG sparklines, and area chart for selected ticker via Zustand selectors**

## Performance

- **Duration:** 6 min
- **Started:** 2026-03-17T07:24:27Z
- **Completed:** 2026-03-17T07:30:27Z
- **Tasks:** 2
- **Files modified:** 8

## Accomplishments
- Watchlist component renders all tickers with per-ticker Zustand selectors for optimal re-rendering
- Price flash animations (green uptick / red downtick) with 500ms CSS transition fade
- SVG polyline sparklines accumulating from SSE price history
- MainChart displays selected ticker's price history as Lightweight Charts area series
- Page layout wires Watchlist and MainChart via selectedTicker state

## Task Commits

Each task was committed atomically:

1. **Task 1: Watchlist with live prices, flash animations, and sparklines** - `b71b045` (feat)
2. **Task 2: Main chart area, page layout integration, and tests** - `e324f52` (feat)

## Files Created/Modified
- `frontend/src/components/Watchlist.tsx` - Watchlist panel with WatchlistRow sub-component, price flash, sparklines, add/remove
- `frontend/src/components/MainChart.tsx` - Area chart for selected ticker using Lightweight Charts
- `frontend/src/__tests__/Watchlist.test.tsx` - 3 tests: rendering, flash classes, click interaction
- `frontend/src/__tests__/MainChart.test.tsx` - 2 tests: null ticker placeholder, chart container rendering
- `frontend/src/setupTests.ts` - jest-dom/vitest matchers + ResizeObserver polyfill
- `frontend/vitest.config.ts` - Added setupFiles configuration
- `frontend/src/app/page.tsx` - Integrated Watchlist + MainChart with selectedTicker state
- `frontend/src/components/PortfolioHeatmap.tsx` - Fixed d3-hierarchy type errors (pre-existing)

## Decisions Made
- Used SVG polyline sparklines instead of Lightweight Charts for mini-charts (simpler at 100x30px)
- Used addAreaSeries() API for LW Charts v4.2.3 compatibility (not newer addSeries(AreaSeries))
- Cast time values to Time type for LW Charts setData type compatibility

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Fixed PortfolioHeatmap d3-hierarchy type errors**
- **Found during:** Task 1 (build verification)
- **Issue:** Pre-existing type errors in PortfolioHeatmap.tsx: hierarchy generic type mismatch and missing x0/y0 properties on HierarchyNode
- **Fix:** Used union type `LeafNode | { children: LeafNode[] }` for hierarchy generic, cast leaves() return to HierarchyRectangularNode
- **Files modified:** frontend/src/components/PortfolioHeatmap.tsx
- **Verification:** Build succeeds
- **Committed in:** b71b045 (Task 1 commit)

**2. [Rule 3 - Blocking] Added vitest setup file with jest-dom matchers**
- **Found during:** Task 1 (test infrastructure)
- **Issue:** toBeInTheDocument() matcher not available - jest-dom not configured for vitest
- **Fix:** Created setupTests.ts importing @testing-library/jest-dom/vitest, added to vitest.config.ts setupFiles
- **Files modified:** frontend/src/setupTests.ts, frontend/vitest.config.ts
- **Verification:** All tests pass with DOM matchers
- **Committed in:** b71b045 (Task 1 commit)

---

**Total deviations:** 2 auto-fixed (2 blocking)
**Impact on plan:** Both fixes necessary for build and test infrastructure. No scope creep.

## Issues Encountered
- LW Charts v4.2.3 does not export AreaSeries class (newer API) -- used addAreaSeries() method instead
- Pre-existing test failures in PnLChart.test.tsx and PositionsTable.test.tsx (components not yet created, future plan scope)

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Watchlist and MainChart components ready for integration with remaining panels
- selectedTicker state pattern established for cross-component communication
- Pre-existing test failures for PnLChart and PositionsTable need components from plan 04-03/04-04

---
*Phase: 04-trading-terminal-frontend*
*Completed: 2026-03-17*
