# Project Research Summary

**Project:** FinAlly — AI Trading Workstation
**Domain:** Single-container AI-powered simulated trading terminal (FastAPI + Next.js + SQLite + SSE + LLM)
**Researched:** 2026-03-16
**Confidence:** HIGH

## Executive Summary

FinAlly is a Bloomberg-inspired trading workstation where the central differentiator is an LLM assistant that can reason about a user's portfolio and execute trades autonomously. The recommended build approach follows a strict dependency chain: database layer first (everything else blocks on it), then portfolio and watchlist APIs, then LLM integration on top of that proven foundation, then the frontend, and finally Docker packaging. The market data subsystem (price simulator, SSE streaming, PriceCache) is already complete and production-ready — it is a given rather than a risk. The frontend is a Next.js 15 static export served by FastAPI on a single port, eliminating CORS entirely. State management is handled by Zustand (selective re-renders for high-frequency price data) and Lightweight Charts (canvas-based financial charting). The stack is lean and well-matched to a single-user demo.

The primary architectural pattern to follow is the router factory pattern already established in the market data subsystem: each API module accepts its dependencies (DB, PriceCache) as arguments and returns an `APIRouter`, with no global state. The FastAPI lifespan context manager orchestrates startup and shutdown. SQLite is used with WAL mode and a busy timeout to handle concurrent async writes from trades, background snapshots, and chat — the single most common failure mode in apps of this type. Trade execution must be wrapped in a `BEGIN IMMEDIATE` transaction from day one; this cannot be retrofitted safely.

The biggest risks in this build are: (1) SQLite write contention from concurrent async operations — prevent with WAL mode + `BEGIN IMMEDIATE` trades; (2) LLM structured output schema drift — prevent with Pydantic validation wrapping every LLM response before any auto-execution; (3) Next.js static export incompatibility — prevent by setting `output: 'export'` on day one and running `next build` frequently. The AI auto-execution feature (the "wow factor") is well-scoped and achievable: the LLM returns structured JSON, Pydantic validates it, and the same trade validation pipeline used by the manual trade bar handles execution. No separate code path for LLM-driven trades.

## Key Findings

### Recommended Stack

The backend is Python 3.12 with FastAPI (already in use), `aiosqlite` for async SQLite access (no ORM needed for 6 simple tables), and LiteLLM `>=1.80.8` for the Gemini `gemini-3.1-flash-lite-preview` integration (day-0 support added in that version). NumPy is already in use for the GBM simulator. Pydantic (a FastAPI dependency) serves double duty: API request/response validation AND LLM structured output schemas.

The frontend is Next.js 15 (not 16 — too new) with React 18, Tailwind CSS v4 (CSS-first config, no tailwind.config.js needed), Lightweight Charts v4.x (canvas-based, purpose-built for streaming financial data), and Zustand 5.x (1KB state library with selector-based surgical re-renders — critical for 500ms price updates across 10 tickers). The native `EventSource` API handles SSE — no library needed. Native `fetch` handles REST calls — no axios needed.

**Core technologies:**
- FastAPI + Uvicorn (with `[standard]`): REST, SSE, static file serving — already proven in this project
- aiosqlite `>=0.22.0`: async SQLite, one connection at startup, WAL mode enabled — avoids blocking the event loop
- LiteLLM `>=1.80.8`: unified LLM gateway with Pydantic `response_format` for structured Gemini output
- Next.js 15 + `output: 'export'`: static SPA served by FastAPI at same origin, zero CORS
- Lightweight Charts 4.x: TradingView's own canvas charting library, handles streaming data at 500ms intervals
- Zustand 5.x: selector-based state management that prevents full re-renders on every price tick
- Tailwind CSS v4: utility-first styling, 70% smaller output than v3, CSS-first config

### Expected Features

**Must have (table stakes) — P1:**
- Live price display with green/red flash animations — defines "alive" feel of a trading terminal
- Watchlist with add/remove (10 default tickers seeded) — users expect this in any trading product
- Buy/sell trade execution (market orders, instant fill, no fees) — a trading platform without trading is not a product
- Positions table: ticker, qty, avg cost, current price, unrealized P&L, % change
- Cash balance and portfolio total value in header (updating live from SSE prices)
- Connection status indicator (green/yellow/red dot) — users must know if data feed is live
- Dark terminal aesthetic (backgrounds ~#0d1117, accent yellow/blue/purple) — the aesthetic promise of the plan
- Main chart area (click ticker to see price history) — gives depth beyond a flat list
- AI chat with portfolio awareness and auto-execution — the core differentiator
- Docker container with start/stop scripts — zero-friction launch for course capstone demo

**Should have (competitive differentiators) — P2:**
- Sparkline mini-charts in watchlist (accumulated from SSE since page load)
- Portfolio heatmap / treemap (positions sized by weight, colored by P&L)
- P&L chart from portfolio snapshots (every 30s + post-trade)
- Inline action confirmations in chat (trade cards showing what the AI executed)
- Trade history view
- LLM mock mode (required for E2E testing, enables development without API key)

**Defer (v2+ or v3):**
- Playwright E2E tests (important for quality, not blocking first demo)
- Frontend unit tests (defer until components stabilize)
- Cloud deployment / Terraform (explicit stretch goal in PLAN.md)
- Limit orders, user auth, options, technical indicators — all explicitly anti-features for this project

### Architecture Approach

The system is a single Docker container on port 8000. FastAPI serves both the API (at `/api/*`) and the Next.js static export (at `/*`). A FastAPI lifespan context manager starts two background tasks on startup: the existing MarketDataSource (simulator or Massive API client) and a new portfolio snapshot recorder (every 30s). The PriceCache (already built) is the central shared-read service — the SSE stream, portfolio API, and trade execution all read from it; only the MarketDataSource writes to it. The DB module (to build) uses a single shared `aiosqlite` connection. The LLM module (to build) separates client logic, prompt formatting, Pydantic schemas, and mock mode into four focused files. All dependencies flow through router factory functions and `app.state`, never global module variables.

**Major components and status:**
1. MarketDataSource + PriceCache + SSE stream router — EXISTS, production-ready
2. DB module (connection, schema.sql, seed.py, queries) — TO BUILD, blocks everything else
3. Portfolio API router (positions, trade execution, history) — TO BUILD, depends on DB
4. Watchlist API router (CRUD + MarketDataSource sync) — TO BUILD, depends on DB
5. LLM module (LiteLLM client, prompts, schemas, mock) — TO BUILD, depends on Portfolio + Watchlist APIs
6. Chat API router (accept message, call LLM, auto-execute, store) — TO BUILD, depends on LLM module
7. Snapshot background task (every 30s + post-trade trigger) — TO BUILD, designed with DB layer
8. app/main.py lifespan orchestration — TO BUILD, wires everything together
9. Next.js frontend (all UI panels) — TO BUILD, depends on all API contracts

### Critical Pitfalls

1. **SQLite write contention ("database is locked")** — enable `PRAGMA journal_mode=WAL` and `PRAGMA busy_timeout=5000` at connection creation time; wrap all trade logic in `BEGIN IMMEDIATE` transactions. Do this in the DB layer from day one — it cannot be retrofitted without risk.

2. **Trade execution race condition (double-spend on cash)** — the read-validate-write sequence must be atomic. Use `BEGIN IMMEDIATE` to acquire a write lock at transaction start. The LLM auto-execution path and the manual trade bar must call the same shared trade function, never duplicate validation logic.

3. **LLM structured output schema drift** — `gemini-3.1-flash-lite-preview` is a preview model; structured output adherence is not guaranteed. Validate every LLM response through Pydantic models before any auto-execution. Enable `litellm.enable_json_schema_validation = True`. Wrap auto-execution in try/except with graceful degradation.

4. **Lightweight Charts SSR crash** — the library accesses `window` at import time; Next.js pre-renders even static exports. Wrap every chart component in `dynamic(() => import(...), { ssr: false })`. Establish this pattern on the first chart component and apply consistently.

5. **Next.js static export feature incompatibility** — `next/image` optimization, API routes, middleware, and `getServerSideProps` all fail with `output: 'export'`. Set `output: 'export'` and `images: { unoptimized: true }` in `next.config.js` on the first commit and run `next build` before adding any features.

## Implications for Roadmap

Based on research, the build follows a clear dependency chain with minimal opportunity for parallelism (except that frontend scaffolding can begin as soon as API contracts are defined). The suggested 7-phase structure:

### Phase 1: Database Layer
**Rationale:** The dependency graph is unambiguous — every other backend component reads from or writes to SQLite. Nothing else can be built without this foundation. This is the first bottleneck per the architecture research.
**Delivers:** `backend/app/db/` module with `aiosqlite` connection management, `schema.sql` (6 tables), lazy init + seed (default user, 10 tickers), and typed query functions for all domains.
**Addresses:** Database layer prerequisite for all P1 features.
**Avoids:** SQLite write contention (configure WAL + busy_timeout here), "database is locked" errors (Pitfall 1), background task lifecycle failure (Pitfall 7).
**Research flag:** Standard patterns — skip phase research. aiosqlite raw SQL is well-documented.

### Phase 2: Portfolio and Watchlist APIs
**Rationale:** These two APIs form the core trading loop and are tightly coupled (watchlist removal must coordinate with MarketDataSource to keep tracking held tickers). They also define the API contract the frontend needs to begin work. Build together — they share the DB module and both are needed before the LLM can inject portfolio context.
**Delivers:** `GET/POST /api/portfolio`, `POST /api/portfolio/trade`, `GET /api/portfolio/history`, `GET/POST/DELETE /api/watchlist/*`, portfolio snapshot background task, `GET /api/health`.
**Addresses:** Trade execution (P1), positions table data (P1), cash balance (P1), watchlist CRUD (P1), P&L chart data source (P2).
**Avoids:** Trade race conditions — `BEGIN IMMEDIATE` transaction from day one (Pitfall 2). Portfolio snapshot background task designed with DB layer, not retrofitted (Pitfall 7). Shared trade function (no duplicate validation) — Anti-pattern 3.
**Research flag:** Standard patterns — skip phase research. FastAPI router factory pattern already proven in codebase.

### Phase 3: LLM Chat Integration
**Rationale:** The AI chat is the core differentiator but depends on all of Phase 2 (needs portfolio context for prompts, needs trade execution for auto-execution, needs watchlist API for watchlist changes). Build last among backend phases — it is the integration layer over everything else.
**Delivers:** `backend/app/llm/` module (client, prompts, schemas, mock), `POST /api/chat` endpoint with structured output parsing, Pydantic response validation, auto-execution through Phase 2 trade/watchlist functions, `LLM_MOCK=true` mode, chat history persistence.
**Addresses:** AI chat with portfolio awareness (P1 differentiator), AI auto-execution (P1 wow factor), AI watchlist management (P1), LLM mock mode (P2).
**Avoids:** LLM schema drift — Pydantic validation wrapping every response before auto-execution (Pitfall 3). LLM prompt injection — all LLM-proposed trades go through the same validation pipeline as manual trades.
**Research flag:** Needs attention during implementation. `gemini-3.1-flash-lite-preview` is a preview model; structured output adherence needs verification at build time. Fallback: `gemini-2.0-flash-lite` if structured output is unreliable.

### Phase 4: Backend Wiring (app/main.py)
**Rationale:** With all backend modules built, `main.py` can wire them together using the lifespan pattern. This is intentionally deferred — trying to write the lifespan before all modules exist leads to placeholder stubs and integration surprises.
**Delivers:** `backend/app/main.py` with FastAPI lifespan (DB init, MarketDataSource start, snapshot task start, router mounting, static file serving), full integrated backend runnable with `uvicorn`.
**Addresses:** Single-container architecture, zero-friction start, health check endpoint.
**Avoids:** Global state anti-pattern — all dependencies flow through `app.state` and router factory arguments. Static file serving order — API routers mounted before static file catch-all.
**Research flag:** Standard patterns — lifespan pattern is documented FastAPI approach, already proven in codebase.

### Phase 5: Frontend
**Rationale:** The frontend depends on all API contracts being stable. Beginning frontend work after the backend is complete eliminates the need for mock servers and API contract churn. The Next.js static export must be configured correctly from the first commit.
**Delivers:** Complete Next.js 15 frontend — dark terminal layout, watchlist panel with price flash animations, sparkline mini-charts, main chart area (Lightweight Charts), portfolio heatmap (treemap), P&L chart, positions table, trade bar, AI chat panel, header with live portfolio value and connection status indicator. Zustand stores for price state. EventSource singleton for SSE. Typed fetch wrappers in `lib/api.ts`.
**Addresses:** All P1 frontend features, all P2 visual features.
**Avoids:** Next.js static export incompatibility — `output: 'export'` on first commit, `next build` before adding features (Pitfall 6). Lightweight Charts SSR crash — `dynamic import` with `ssr: false` on first chart component (Pitfall 4). SSE connection limit — EventSource as singleton with `useEffect` cleanup (Pitfall 5). Full watchlist re-render on every SSE tick — `React.memo` on ticker rows, Zustand selectors per ticker.
**Research flag:** Needs attention during implementation for treemap library selection (d3-hierarchy vs lightweight alternative) and Lightweight Charts v4 React integration pattern (no official React wrapper — use refs + useEffect).

### Phase 6: Docker and Scripts
**Rationale:** Packaging is the last step — the multi-stage Dockerfile copies the Next.js static export into the Python image, which can only happen once both are complete and the frontend build produces a clean `out/` directory.
**Delivers:** Multi-stage Dockerfile (Node 20 build stage, Python 3.12 runtime), `scripts/start_mac.sh`, `scripts/stop_mac.sh`, `scripts/start_windows.ps1`, `scripts/stop_windows.ps1`, `.env.example`, named Docker volume for SQLite persistence.
**Addresses:** Zero-friction single-command launch (P1), `db/` volume persistence.
**Avoids:** SQLite path misconfiguration — backend writes to `/app/db/finally.db` (mounted path), not a relative path.
**Research flag:** Standard patterns — multi-stage Docker builds and volume mounts are well-documented.

### Phase 7: Testing
**Rationale:** Unit tests for the backend can be written alongside earlier phases. This phase captures the E2E Playwright test suite, which requires the full Docker stack to be operational.
**Delivers:** Backend unit tests (portfolio logic, LLM structured output parsing, trade validation edge cases), frontend component tests (Vitest + React Testing Library), Playwright E2E tests in `test/docker-compose.test.yml` with `LLM_MOCK=true`.
**Addresses:** Quality assurance for all core user flows.
**Research flag:** Standard patterns for unit tests. E2E test scenarios are specified in PLAN.md — no additional research needed.

### Phase Ordering Rationale

- DB layer precedes all other backend phases because every API endpoint reads or writes SQLite — this is a hard dependency, not a preference.
- Portfolio and Watchlist APIs are grouped in one phase because watchlist removal must coordinate with the MarketDataSource (already built), and both are required inputs for the LLM context injection in Phase 3.
- LLM integration comes third because it is an orchestration layer over the trade execution and watchlist functions from Phase 2 — building it first would require stubs.
- Backend wiring (`main.py`) comes fourth because it requires all modules to exist before it can wire them. Writing it early creates churn.
- Frontend comes fifth because stable API contracts eliminate the need for frontend mocking and prevent API contract churn mid-development.
- Docker comes sixth because the multi-stage build requires both a completed frontend build output and a working backend.
- Testing comes last for E2E (requires Docker), but unit tests should be written alongside each phase.

### Research Flags

Phases needing attention during implementation:
- **Phase 3 (LLM Chat):** `gemini-3.1-flash-lite-preview` is a preview model. Verify structured output reliability at build time. Have `gemini-2.0-flash-lite` as documented fallback. Test with adversarial prompts early.
- **Phase 5 (Frontend):** Treemap library selection is unresolved — `d3-hierarchy` is the standard but adds bundle size; a lighter alternative may exist. Lightweight Charts v4 React integration uses refs + useEffect (no official wrapper) — verify the pattern against v4 docs before building chart components.

Phases with standard patterns (can proceed without phase research):
- **Phase 1 (Database):** aiosqlite + raw SQL is well-documented. WAL mode pragmas are established practice.
- **Phase 2 (Portfolio/Watchlist APIs):** Router factory pattern is already proven in this codebase.
- **Phase 4 (Backend Wiring):** FastAPI lifespan is documented and follows existing codebase patterns.
- **Phase 6 (Docker):** Multi-stage builds and volume mounts are standard Docker practice.
- **Phase 7 (Testing):** pytest-asyncio and Vitest patterns are well-documented; E2E scenarios are specified in PLAN.md.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Backend stack already proven in this codebase. LiteLLM Gemini support documented at specific version. Frontend library choices are industry-standard for the use case. One gap: LiteLLM structured output with preview model needs runtime verification. |
| Features | HIGH | Feature set is tightly defined in PLAN.md. Research confirmed which are table stakes vs differentiators. Anti-features are clearly scoped out. Dependency graph is unambiguous. |
| Architecture | HIGH | Component boundaries, data flow, and build order are clear and consistent across all research files. Router factory pattern already proven in existing market data subsystem. The "TO BUILD" components have no architectural ambiguity. |
| Pitfalls | HIGH | All 7 critical pitfalls are sourced from official documentation, known library issues, and established SQLite/async patterns. Prevention strategies are specific and actionable. Each pitfall has a phase assignment for when to address it. |

**Overall confidence:** HIGH

### Gaps to Address

- **LiteLLM + `gemini-3.1-flash-lite-preview` structured output:** The model is marked as preview. The `response_format` Pydantic approach is documented for Gemini but has known edge cases in LiteLLM's issue tracker. Mitigation: validate with Pydantic before any auto-execution, enable `litellm.enable_json_schema_validation = True`, and document the `gemini-2.0-flash-lite` fallback string in the codebase.
- **Treemap library selection:** No specific recommendation is locked in FEATURES.md or ARCHITECTURE.md beyond "d3-based or lightweight alternative." This needs a concrete choice when Phase 5 begins. Suggested: evaluate `d3-hierarchy` directly (no full D3 bundle needed, just the treemap layout algorithm) vs a pre-built React treemap component.
- **Sparkline implementation detail:** Both the watchlist sparklines and the main chart area share a price history accumulation pattern from SSE. This shared hook (`usePriceHistory`) should be designed once in Phase 5 scaffolding and reused — the research flags this as an optimization opportunity, not a risk.

## Sources

### Primary (HIGH confidence)
- [FastAPI Lifespan Events](https://fastapi.tiangolo.com/advanced/events/) — lifespan context manager pattern
- [FastAPI Static Files](https://fastapi.tiangolo.com/tutorial/static-files/) — `html=True` SPA fallback
- [LiteLLM Structured Outputs](https://docs.litellm.ai/docs/completion/json_mode) — Pydantic `response_format` with Gemini
- [LiteLLM Gemini 3.1 Flash Lite Preview support](https://docs.litellm.ai/blog/gemini_3_1_flash_lite_preview) — v1.80.8+ day-0 support
- [Next.js Static Exports guide](https://nextjs.org/docs/app/guides/static-exports) — `output: 'export'` configuration
- [Next.js API Routes in Static Export warning](https://nextjs.org/docs/messages/api-routes-static-export) — incompatibility confirmation
- [SQLite WAL mode documentation](https://sqlite.org/wal.html) — concurrent write configuration
- [aiosqlite PyPI](https://pypi.org/project/aiosqlite/) — v0.22.1, async SQLite bridge
- [Lightweight Charts documentation](https://tradingview.github.io/lightweight-charts/docs) — v4.x usage
- [Zustand GitHub](https://github.com/pmndrs/zustand) — v5.0.12 selector patterns
- [Tailwind CSS v4 announcement](https://tailwindcss.com/blog/tailwindcss-v4) — CSS-first config

### Secondary (MEDIUM confidence)
- [SQLite concurrent writes and "database is locked"](https://tenthousandmeters.com/blog/sqlite-concurrent-writes-and-database-is-locked-errors/) — WAL mode + busy_timeout practice
- [LiteLLM + Gemini structured output issues (GitHub)](https://github.com/openai/openai-agents-python/issues/1575) — known edge cases with preview models
- [Understanding Race Conditions in Automated Trading](https://blog.traderspost.io/article/understanding-race-conditions-in-automated-trading) — `BEGIN IMMEDIATE` pattern

### Tertiary (LOW confidence)
- [Gemini 3.1 Flash-Lite model page](https://ai.google.dev/gemini-api/docs/models/gemini-3.1-flash-lite-preview) — preview model specs (needs runtime verification)

---
*Research completed: 2026-03-16*
*Ready for roadmap: yes*
