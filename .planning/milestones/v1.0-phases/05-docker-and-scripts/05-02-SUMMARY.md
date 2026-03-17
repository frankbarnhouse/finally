---
phase: 05-docker-and-scripts
plan: 02
subsystem: infra
tags: [docker, bash, powershell, scripts, devops]

requires:
  - phase: 05-docker-and-scripts/01
    provides: Dockerfile for building the container image
provides:
  - macOS/Linux start and stop scripts (bash)
  - Windows PowerShell start and stop scripts
  - Single-command app launch for both platforms
affects: [06-testing-and-polish]

tech-stack:
  added: []
  patterns: [idempotent scripts, platform-specific wrappers]

key-files:
  created:
    - scripts/start_mac.sh
    - scripts/stop_mac.sh
    - scripts/start_windows.ps1
    - scripts/stop_windows.ps1
  modified: []

key-decisions:
  - "Idempotent scripts that detect already-running containers and skip re-launch"
  - "Auto-build image if not present; --build flag for forced rebuild"

patterns-established:
  - "Docker wrapper scripts: constants at top, Docker check, conditional build, idempotent run"

requirements-completed: [INFRA-02, INFRA-03]

duration: 1min
completed: 2026-03-17
---

# Phase 5 Plan 2: Start/Stop Scripts Summary

**Docker wrapper scripts for macOS/Linux (bash) and Windows (PowerShell) with idempotent launch, volume persistence, and browser-open flags**

## Performance

- **Duration:** 1 min
- **Started:** 2026-03-17T09:24:06Z
- **Completed:** 2026-03-17T09:25:21Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- Four platform scripts providing single-command app launch and shutdown
- Idempotent behavior: safe to run multiple times without errors
- Data persistence via named Docker volume (never removed by stop scripts)

## Task Commits

Each task was committed atomically:

1. **Task 1: Create macOS/Linux start and stop scripts** - `5759baf` (feat)
2. **Task 2: Create Windows PowerShell start and stop scripts** - `d1a8481` (feat)

## Files Created/Modified
- `scripts/start_mac.sh` - Bash script to build (if needed) and launch container with volume, port, and env
- `scripts/stop_mac.sh` - Bash script to stop and remove container, preserving Docker volume
- `scripts/start_windows.ps1` - PowerShell equivalent of start_mac.sh with param blocks
- `scripts/stop_windows.ps1` - PowerShell equivalent of stop_mac.sh

## Decisions Made
- Idempotent scripts that detect already-running containers and skip re-launch
- Auto-build image if not present; --build / -Build flag for forced rebuild
- Browser open via --open flag (macOS: open, Linux: xdg-open, Windows: Start-Process)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All Docker infrastructure complete (Dockerfile + scripts)
- Ready for Phase 6 testing and polish

---
*Phase: 05-docker-and-scripts*
*Completed: 2026-03-17*
