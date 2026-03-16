---
phase: 02-portfolio-and-watchlist-apis
plan: 02
subsystem: api
tags: [fastapi, watchlist, health-check, sqlite, sse]

requires:
  - phase: 01-database-foundation
    provides: "SQLite schema, get_db singleton, seed_defaults"
provides:
  - "GET/POST/DELETE /api/watchlist endpoints with price enrichment"
  - "GET /api/health endpoint"
  - "Watchlist service with position-aware ticker removal"
affects: [03-llm-chat-integration, 04-frontend-terminal-ui]

tech-stack:
  added: [httpx (test only)]
  patterns: [router-factory-with-dependency-injection, service-layer-separation]

key-files:
  created:
    - backend/app/services/watchlist.py
    - backend/app/api/watchlist.py
    - backend/app/api/health.py
    - backend/tests/api/test_watchlist.py
    - backend/tests/api/test_health.py
  modified: []

key-decisions:
  - "Watchlist service as standalone module separate from API router for testability"
  - "Position-aware removal: remove_ticker checks positions table before calling data_source.remove_ticker()"

patterns-established:
  - "Service-layer pattern: app/services/*.py for business logic, app/api/*.py for HTTP routing"
  - "API test pattern: FastAPI test app with AsyncClient + ASGITransport + monkeypatched DB"

requirements-completed: [WATCH-01, WATCH-02, WATCH-03, INFRA-04]

duration: 2min
completed: 2026-03-16
---

# Phase 2 Plan 2: Watchlist & Health API Summary

**Watchlist CRUD endpoints with PriceCache enrichment, position-aware removal safety, and health check for Docker deployment**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-16T19:00:04Z
- **Completed:** 2026-03-16T19:01:54Z
- **Tasks:** 2
- **Files modified:** 8

## Accomplishments
- GET /api/watchlist returns all tickers with live prices from PriceCache (or null if unavailable)
- POST /api/watchlist adds uppercase-normalized tickers with idempotent INSERT OR IGNORE
- DELETE /api/watchlist/{ticker} removes from watchlist but preserves price tracking when user holds a position
- GET /api/health returns {"status": "ok"} for Docker/deployment health checks
- 10 tests covering all endpoints, edge cases, and position-aware safety

## Task Commits

Each task was committed atomically:

1. **Task 1: Watchlist service and API endpoints** - `bc7ecc3` (test) + `0c8a828` (feat) [TDD]
2. **Task 2: Health check endpoint** - `d8e73c5` (feat)

_Note: Task 1 used TDD flow (RED: failing tests, GREEN: implementation)_

## Files Created/Modified
- `backend/app/services/watchlist.py` - Watchlist CRUD business logic (get, add, remove)
- `backend/app/api/watchlist.py` - REST endpoints with router factory pattern
- `backend/app/api/health.py` - Health check endpoint
- `backend/tests/api/test_watchlist.py` - 9 tests for watchlist API
- `backend/tests/api/test_health.py` - 1 test for health endpoint
- `backend/app/services/__init__.py` - Package init
- `backend/app/api/__init__.py` - Package init
- `backend/tests/api/__init__.py` - Package init

## Decisions Made
- Watchlist service as standalone module separate from API router for testability
- Position-aware removal: remove_ticker checks positions table before calling data_source.remove_ticker()

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

Pre-existing issue: `tests/services/test_portfolio.py` (from parallel Plan 02-01) imports `app.services.portfolio` which does not yet exist, causing collection error when running full `tests/` suite. This is expected with parallel plan execution and not caused by this plan's changes. All tests in `tests/db/`, `tests/api/`, and `tests/market/` pass (88 total).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Watchlist endpoints ready for frontend integration
- Health endpoint ready for Docker HEALTHCHECK directive
- Service layer pattern established for portfolio service (Plan 02-01)

---
*Phase: 02-portfolio-and-watchlist-apis*
*Completed: 2026-03-16*
