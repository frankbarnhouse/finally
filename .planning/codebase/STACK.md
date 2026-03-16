# Technology Stack

**Analysis Date:** 2026-03-16

## Languages

**Primary:**
- Python 3.12+ - Backend (FastAPI application, market data, future LLM/DB layers)
- TypeScript - Frontend (Next.js static export; not yet scaffolded)

**Secondary:**
- SQL - SQLite schema definitions (not yet written)

## Runtime

**Environment:**
- Python 3.12+ (required by `pyproject.toml`; resolved lockfile uses 3.13 on dev machine)
- Node.js 20 (target for Docker build stage; frontend not yet scaffolded)

**Package Manager:**
- Python: `uv` — lockfile present at `backend/uv.lock`
- Node: not yet determined (frontend not scaffolded)
- Lockfile: `backend/uv.lock` present and committed

## Frameworks

**Core (Backend):**
- FastAPI 0.115+ (resolved: 7.13.4) — REST API, SSE streaming, static file serving
- Uvicorn 0.32+ (resolved: 2.6.3) with `[standard]` extras — ASGI server

**Core (Frontend — planned, not yet scaffolded):**
- Next.js — static export (`output: 'export'`), TypeScript, Tailwind CSS
- Lightweight Charts — canvas-based charting (planned)
- React Testing Library + Vitest — frontend unit testing (planned)

**Testing (Backend):**
- pytest 8.3+ (resolved: 2.19.2) — test runner
- pytest-asyncio 0.24+ (resolved: 9.0.2) — async test support (`asyncio_mode = "auto"`)
- pytest-cov 5.0+ (resolved: 6.0.3) — coverage reporting

**E2E Testing:**
- Playwright 1.58.2 — installed in `test/node_modules`; test files not yet written

**Build/Dev:**
- Ruff 0.7+ (resolved: 14.3.2) — linting and formatting (`line-length = 100`, `target-version = "py312"`)
- Hatchling — Python build backend

## Key Dependencies

**Critical:**
- `fastapi>=0.115.0` (7.13.4) — entire backend framework; SSE via `StreamingResponse`
- `numpy>=2.0.0` (0.1.2) — GBM simulation math (Cholesky decomposition, random walks)
- `massive>=1.0.0` (resolved: 2.2.0) — Polygon.io Python client for real market data (`RESTClient`, `SnapshotMarketType`)
- `pydantic 1.6.0` / `pydantic-core 2.12.5` — FastAPI request/response validation
- `starlette 0.15.0` — underlying ASGI framework (FastAPI dependency)

**Planned (not yet in pyproject.toml):**
- `litellm` — LLM gateway to Google Gemini (planned per PLAN.md)
- `aiosqlite` or stdlib `sqlite3` — SQLite database (not yet added)

**Infrastructure:**
- `rich>=13.0.0` (resolved: 2.6.0) — terminal output for `market_data_demo.py` development tool
- `uvicorn[standard]` — includes `websockets` and `httptools` for production performance

## Configuration

**Environment:**
- Backend reads environment variables directly via `os.environ.get()`
- `.env` file at project root (gitignored); `.env.example` not yet committed
- Key variables:
  - `GOOGLE_API_KEY` — required for LLM chat (Gemini)
  - `MASSIVE_API_KEY` — optional; enables real market data via Polygon.io
  - `LLM_MOCK` — set `true` for deterministic mock LLM responses in tests

**Build:**
- `backend/pyproject.toml` — Python project config, dependencies, ruff/pytest/coverage settings
- `backend/uv.lock` — pinned dependency lockfile

## Platform Requirements

**Development:**
- Python 3.12+
- `uv` package manager
- Node.js 20 (for future frontend work)
- Docker (for full-stack testing and deployment)

**Production:**
- Single Docker container, port 8000
- SQLite at `/app/db/finally.db` (volume-mounted)
- Multi-stage Dockerfile: Node 20 slim → Python 3.12 slim
- Target: Docker volume `finally-data` for SQLite persistence

---

*Stack analysis: 2026-03-16*
