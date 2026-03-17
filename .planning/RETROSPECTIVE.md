# Project Retrospective

*A living document updated after each milestone. Lessons feed forward into future planning.*

## Milestone: v1.0 — FinAlly MVP

**Shipped:** 2026-03-17
**Phases:** 6 | **Plans:** 15

### What Was Built
- SQLite database with lazy init, 6-table schema, WAL mode, and automatic seeding
- Portfolio and trade APIs with transactional safety, watchlist CRUD with position-aware removal
- LLM chat integration via LiteLLM + Gemini with structured outputs, auto-execution, and mock mode
- Bloomberg-inspired dark trading terminal with live SSE prices, flash animations, sparklines, charts, heatmap, and chat panel
- Multi-stage Dockerfile (Node 22 + Python 3.12) with start/stop scripts
- Comprehensive test suite: 127+ backend, 24 frontend, 8 E2E scenarios

### What Worked
- **Wave-based parallel execution** — Plans 02-01/02-02 and 04-02/04-03 ran in parallel, significantly reducing wall-clock time
- **TDD approach** — writing tests first caught integration issues early (e.g., Zustand store patterns, aiosqlite async handling)
- **Service-layer separation** — building portfolio/watchlist as services in Phase 2 made Phase 3's LLM auto-execution trivial
- **Router factory pattern** — consistent dependency injection across all API routers enabled clean testing

### What Was Inefficient
- **Plan 04-01 scope** — 20 files in the frontend scaffold plan was too large initially, caught by plan checker and split
- **VALIDATION.md frontmatter** — never updated post-execution across any phase, leaving nyquist_compliant=false everywhere
- **litellm missing from pyproject.toml** — dependency was used but not declared, only caught during Docker build

### Patterns Established
- Router factory pattern for all FastAPI endpoints: `create_X_router(dependencies)`
- Zustand stores with per-item selectors to avoid SSE re-render cascades
- BEGIN IMMEDIATE transactions for all trade operations
- Service layer callable by both HTTP routes and LLM chat auto-execution

### Key Lessons
1. Always declare dependencies in pyproject.toml when adding new imports — Docker builds fail late otherwise
2. Frontend scaffold plans need extra scope scrutiny — many small config/type files add up fast
3. Service-layer separation pays for itself immediately when the LLM integration phase needs to reuse trade/watchlist logic
4. Plan checker revision loop is valuable — caught both scope and Nyquist issues before execution

### Cost Observations
- Model mix: Quality profile (Opus for planning/research, Sonnet for verification/synthesis)
- Notable: Parallel Wave 2 execution in Phase 4 was the biggest efficiency win

---

## Cross-Milestone Trends

### Process Evolution

| Milestone | Phases | Plans | Key Change |
|-----------|--------|-------|------------|
| v1.0 | 6 | 15 | Initial build — established all patterns |

### Cumulative Quality

| Milestone | Backend Tests | Frontend Tests | E2E Scenarios |
|-----------|--------------|----------------|---------------|
| v1.0 | 127+ | 24 | 8 |

### Top Lessons (Verified Across Milestones)

1. Service-layer separation enables clean LLM integration
2. Parallel wave execution is the biggest efficiency lever
