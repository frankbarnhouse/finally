# Stack Research

**Domain:** AI-powered trading workstation (FastAPI + Next.js + SQLite + SSE + LLM)
**Researched:** 2026-03-16
**Confidence:** HIGH

## Recommended Stack

### Core Technologies — Backend (Python)

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| FastAPI | >=0.115.0 | REST API, SSE streaming, static file serving | Already in use. Async-native, Pydantic validation built-in, StreamingResponse for SSE. No reason to change. |
| Uvicorn | >=0.32.0 (with `[standard]`) | ASGI server | Already in use. `[standard]` extras include httptools and uvloop for production performance. |
| LiteLLM | >=1.80.8 | LLM gateway to Gemini | Day-0 support for `gemini/gemini-3.1-flash-lite-preview` added in v1.80.8. Unified completion API with structured output via `response_format`. Current stable: 1.82.2. |
| aiosqlite | >=0.22.0 | Async SQLite access | Asyncio bridge to stdlib sqlite3. Avoids blocking the event loop during DB operations. Lightweight, no ORM overhead. Current: 0.22.1. |
| Pydantic | (via FastAPI) | Request/response validation, LLM structured output schemas | Already a FastAPI dependency. Define Pydantic models for trade requests, portfolio responses, AND LLM structured output schemas. One tool for both API validation and LLM output parsing. |
| NumPy | >=2.0.0 | GBM simulation math | Already in use for market data simulator. No changes needed. |

### Core Technologies — Frontend (TypeScript)

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Next.js | 15.x | React framework with static export | Use Next.js 15 (not 16). Next.js 16 was released Oct 2025 and is still maturing. 15 has proven static export support and wider ecosystem compatibility. `output: 'export'` in next.config.js produces pure static files served by FastAPI. |
| React | 18.x | UI framework | Ship with React 18 (Next.js 15 default). React 19 adoption is still early and unnecessary for this project's needs. |
| Tailwind CSS | 4.x | Utility-first styling | v4 has CSS-first config (no tailwind.config.js needed), automatic content detection, 70% smaller output than v3. Current: 4.2.1. Install with `@tailwindcss/postcss` and `postcss`. |
| Lightweight Charts | 4.x | Canvas-based financial charts | TradingView's charting library. 45KB, performant HTML5 canvas rendering, built for streaming financial data. Ideal for sparklines and main chart. Current: 5.1.0 but use 4.x for stability — v5 is recent. |
| Zustand | 5.x | Client state management | Tiny (1KB), no providers/boilerplate, hook-based. Perfect for managing price cache, selected ticker, portfolio state. Current: 5.0.12. Preferred over Redux (too heavy) or React Context (re-render issues with frequent price updates). |
| TypeScript | 5.x | Type safety | Non-negotiable for a project this size. Catches API contract mismatches at compile time. |

### Supporting Libraries — Backend

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| massive | >=1.0.0 | Polygon.io REST client | Already in use for real market data. Only active when `MASSIVE_API_KEY` is set. |
| rich | >=13.0.0 | Terminal output | Already in use for development demo script only. Not a production dependency. |

### Supporting Libraries — Frontend

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| @testing-library/react | latest | Component testing | Unit tests for React components — render, query, assert. |
| @testing-library/user-event | latest | User interaction simulation | Simulating clicks, typing in trade bar, chat input. |
| @testing-library/jest-dom | latest | DOM matchers | Extended matchers like `toBeVisible()`, `toHaveTextContent()`. |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| uv | Python package management | Already in use. Always `uv run`, never `python3` directly. `uv sync --extra dev` for dev deps. |
| Ruff | Python linting/formatting | Already configured: line-length 100, target py312. |
| pytest + pytest-asyncio | Python testing | Already configured with `asyncio_mode = "auto"`. |
| Vitest | Frontend unit testing | Vite-native test runner, Jest-compatible API. Faster than Jest, no config overhead for Vite-based builds. |
| Playwright | E2E testing | Already installed (1.58.2) in `test/`. Runs in separate docker-compose for E2E. |
| ESLint | Frontend linting | Included by `create-next-app`. Standard config. |

## Installation

```bash
# Backend — new dependencies to add
cd backend
uv add "litellm>=1.80.8"
uv add "aiosqlite>=0.22.0"

# Frontend — scaffold and install
npx create-next-app@15 frontend --typescript --tailwind --eslint --app --src-dir --no-import-alias
cd frontend
npm install lightweight-charts@^4.2.0
npm install zustand@^5.0.0

# Frontend dev dependencies
npm install -D vitest @vitejs/plugin-react jsdom
npm install -D @testing-library/react @testing-library/jest-dom @testing-library/user-event
```

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| aiosqlite | SQLAlchemy async | If you need ORM features, complex queries, or migrations. Overkill for this project — we have 6 simple tables with straightforward CRUD. Raw SQL is clearer for a teaching project. |
| Zustand | Redux Toolkit | If you need middleware, devtools integration, or complex state graphs. Unnecessary here — our state is simple (prices, portfolio, selected ticker). |
| Zustand | React Context | Never for frequently-updating data (prices). Context triggers full subtree re-renders on every update. Zustand uses selectors for surgical re-renders. |
| Lightweight Charts (v4) | Recharts | If you want declarative React charts for simple visualizations. But Recharts uses SVG (slow with streaming data) and lacks financial chart types (candlestick, crosshair). |
| Lightweight Charts (v4) | D3.js | If you need fully custom visualizations. Massive API surface, steep learning curve, no built-in financial chart types. |
| LiteLLM | Direct google-genai SDK | If you want zero abstraction. But LiteLLM provides a unified API that makes it trivial to swap models later, and its structured output handling for Gemini is battle-tested. |
| Next.js 15 | Next.js 16 | When 16.x reaches broader adoption and plugin ecosystem catches up. For a static export project built in March 2026, 15 is the safer choice. |
| Tailwind v4 | Tailwind v3 | Only if you have an existing v3 codebase. For new projects, v4 is strictly better (smaller output, simpler config, faster builds). |
| Vitest | Jest | Only if you are already invested in Jest config. Vitest is faster, Vite-native, and Jest-API-compatible. No reason to choose Jest for a new project. |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| SQLAlchemy | ORM complexity is unnecessary for 6 simple tables. Adds abstraction that obscures the SQL — bad for a teaching project. | aiosqlite with raw SQL |
| WebSockets (for prices) | Bidirectional comms not needed. SSE is simpler, has built-in browser reconnection via EventSource, and is already implemented. | SSE via StreamingResponse (already done) |
| Redux | 4x the bundle size of Zustand, requires boilerplate (slices, reducers, store setup). Massive overkill for this app's state. | Zustand |
| Chart.js | SVG-based, poor performance with streaming real-time data. Not designed for financial charts. | Lightweight Charts |
| Prisma / Drizzle | TypeScript ORMs for the frontend talking to a DB. Our frontend talks to the API, not the DB. Backend uses Python. | aiosqlite on the backend |
| axios | Unnecessary dependency. Native `fetch` is supported everywhere and is simpler. | Native fetch API |
| Socket.IO | Heavy library for bidirectional real-time. We only need server-to-client push. EventSource is built into browsers. | Native EventSource |
| React Query / TanStack Query | Useful for complex data fetching with caching, pagination, optimistic updates. Our data flow is simpler — SSE pushes prices, REST fetches portfolio. Would add complexity without benefit. | Direct fetch + Zustand |

## Stack Patterns

**For SSE price streaming:**
- Frontend uses native `EventSource` API (no library needed)
- Zustand store receives price updates and triggers selective re-renders via selectors
- Components subscribe to specific tickers: `usePriceStore(state => state.prices['AAPL'])`

**For LLM structured output:**
- Define Pydantic models for the response schema (message, trades, watchlist_changes)
- Pass `response_format={"type": "json_object", "response_schema": Model.model_json_schema()}` to `litellm.completion()`
- Parse response with `Model.model_validate_json(response.choices[0].message.content)`

**For SQLite with async FastAPI:**
- Use `aiosqlite.connect()` as async context manager
- Connection pool is unnecessary for single-user SQLite — one connection per request is fine
- Lazy initialization: check tables exist on startup, create + seed if missing

**For static export + FastAPI serving:**
- Next.js builds to `out/` directory via `output: 'export'`
- FastAPI mounts `StaticFiles` at `/` with `html=True` for SPA routing
- API routes at `/api/*` take priority over static file serving

## Version Compatibility

| Package A | Compatible With | Notes |
|-----------|-----------------|-------|
| Next.js 15.x | React 18.x | Default pairing. Do not upgrade to React 19 separately. |
| Next.js 15.x | Tailwind CSS 4.x | Fully supported. `create-next-app@15 --tailwind` sets up v4 automatically. |
| LiteLLM >=1.80.8 | gemini/gemini-3.1-flash-lite-preview | Day-0 support added in this version. Use `>=1.80.8` minimum. |
| aiosqlite 0.22.x | Python 3.12+ | Requires Python >=3.9, fully compatible with 3.12+. |
| Lightweight Charts 4.x | React 18.x | No React wrapper needed — use refs and `useEffect` for lifecycle. Official `lightweight-charts-react-wrapper` exists but adds unnecessary abstraction. |
| Zustand 5.x | React 18.x | Full compatibility. |
| Vitest latest | @testing-library/react | Standard pairing. Use `jsdom` environment. |

## Confidence Assessment

| Area | Confidence | Reasoning |
|------|------------|-----------|
| Backend stack (FastAPI, aiosqlite, LiteLLM) | HIGH | FastAPI already proven in this project. aiosqlite is the standard async SQLite library. LiteLLM has documented Gemini 3.1 Flash Lite support. |
| Frontend framework (Next.js 15, Tailwind v4) | HIGH | Well-documented static export path. Tailwind v4 is stable and the official Next.js integration is straightforward. |
| Charting (Lightweight Charts) | HIGH | Industry standard for web-based financial charts. Used by TradingView itself. Canvas-based rendering handles streaming data well. |
| State management (Zustand) | HIGH | Most popular lightweight state library in React ecosystem as of 2026. 4M+ weekly downloads. Perfect fit for streaming price data with selective re-renders. |
| LLM integration pattern | MEDIUM | LiteLLM structured output with Gemini works per docs and examples, but the `gemini-3.1-flash-lite-preview` model is brand new (March 3, 2026). May encounter edge cases with structured output parsing. Fallback: use `gemini-2.0-flash-lite` which is well-proven. |

## Sources

- [LiteLLM Gemini 3.1 Flash Lite Preview support](https://docs.litellm.ai/blog/gemini_3_1_flash_lite_preview) -- Day-0 support announcement, v1.80.8+
- [LiteLLM structured outputs docs](https://docs.litellm.ai/docs/completion/json_mode) -- response_format with Pydantic schemas
- [Next.js static exports guide](https://nextjs.org/docs/app/guides/static-exports) -- output: 'export' configuration
- [Next.js 16.1 blog post](https://nextjs.org/blog/next-16-1) -- confirms 16 exists but is newer
- [Tailwind CSS v4 announcement](https://tailwindcss.com/blog/tailwindcss-v4) -- CSS-first config, performance improvements
- [Tailwind CSS + Next.js setup guide](https://tailwindcss.com/docs/guides/nextjs) -- official installation steps
- [Lightweight Charts npm](https://www.npmjs.com/package/lightweight-charts) -- v5.1.0 latest, v4.x stable
- [Zustand GitHub](https://github.com/pmndrs/zustand) -- v5.0.12, hook-based state management
- [aiosqlite PyPI](https://pypi.org/project/aiosqlite/) -- v0.22.1, async SQLite bridge
- [Vitest + React Testing Library guide](https://nextjs.org/docs/app/guides/testing/vitest) -- official Next.js testing docs
- [Playwright npm](https://www.npmjs.com/package/playwright) -- v1.58.2 stable
- [Gemini 3.1 Flash-Lite model page](https://ai.google.dev/gemini-api/docs/models/gemini-3.1-flash-lite-preview) -- model specs and capabilities

---
*Stack research for: FinAlly AI Trading Workstation*
*Researched: 2026-03-16*
