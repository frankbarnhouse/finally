---
phase: 05-docker-and-scripts
plan: 01
subsystem: infra
tags: [docker, uv, fastapi, static-files, litellm]

requires:
  - phase: 04-trading-terminal-frontend
    provides: Next.js static export (frontend/out/)
  - phase: 03-llm-chat-integration
    provides: Chat service using litellm
provides:
  - Multi-stage Dockerfile building frontend and backend into single container
  - Static file serving in FastAPI for production deployment
  - litellm declared as production dependency
  - .env.example documenting all environment variables
affects: [05-docker-and-scripts]

tech-stack:
  added: [litellm]
  patterns: [multi-stage-docker-build, conditional-static-mount]

key-files:
  created: [Dockerfile, .dockerignore, .env.example]
  modified: [backend/pyproject.toml, backend/uv.lock, backend/app/main.py]

key-decisions:
  - "Conditional static mount: only activates when static/ dir exists (Docker only, no local dev impact)"
  - "uv sync --frozen --no-dev for reproducible production installs"

patterns-established:
  - "Conditional static file serving: check Path.is_dir() before mounting"
  - "Docker layer caching: copy dependency files before application code"

requirements-completed: [INFRA-01]

duration: 2min
completed: 2026-03-17
---

# Phase 5 Plan 1: Dockerfile and Infrastructure Summary

**Multi-stage Docker build (node:22-slim + python:3.12-slim) serving frontend static export and FastAPI backend on port 8000**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-17T09:24:12Z
- **Completed:** 2026-03-17T09:25:37Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- Added litellm as declared dependency in pyproject.toml with regenerated lockfile
- Added conditional static file serving to main.py (activates only in Docker)
- Created multi-stage Dockerfile producing single-container deployment
- Created .dockerignore and .env.example for clean builds and documentation

## Task Commits

Each task was committed atomically:

1. **Task 1: Fix litellm dependency and add static file serving** - `5759baf` (feat)
2. **Task 2: Create Dockerfile, .dockerignore, and .env.example** - `1e3a97a` (feat)

## Files Created/Modified
- `Dockerfile` - Multi-stage build: node:22-slim for frontend, python:3.12-slim for backend
- `.dockerignore` - Excludes .git, node_modules, .venv, __pycache__, .env, test/
- `.env.example` - Documents GOOGLE_API_KEY, MASSIVE_API_KEY, LLM_MOCK
- `backend/pyproject.toml` - Added litellm>=1.80.0 dependency
- `backend/uv.lock` - Regenerated with litellm and transitive dependencies
- `backend/app/main.py` - Conditional StaticFiles mount at "/" when static/ dir exists

## Decisions Made
- Conditional static mount using Path.is_dir() so local dev is unaffected (no static/ dir locally)
- uv sync --frozen --no-dev in Docker for reproducible production-only installs
- Docker layer caching: copy pyproject.toml + uv.lock before app code

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Dockerfile ready for docker build and container deployment
- Start/stop scripts (plan 05-02) can now wrap docker run commands
- Container serves both frontend and backend on single port 8000

## Self-Check: PASSED

All files verified present. All commit hashes verified in git log.

---
*Phase: 05-docker-and-scripts*
*Completed: 2026-03-17*
