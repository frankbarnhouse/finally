# Architecture Research

**Domain:** AI Trading Workstation (single-container FastAPI + static Next.js + SQLite + SSE + LLM)
**Researched:** 2026-03-16
**Confidence:** HIGH

## System Overview

```
┌──────────────────────────────────────────────────────────────────┐
│  Docker Container (port 8000)                                    │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  FastAPI Application (uvicorn)                             │  │
│  │                                                            │  │
│  │  Lifespan Manager                                          │  │
│  │  ├── Init DB (schema + seed)                               │  │
│  │  ├── Start MarketDataSource background task                │  │
│  │  ├── Start portfolio snapshot background task              │  │
│  │  └── Teardown: stop tasks, close DB                        │  │
│  │                                                            │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐  │  │
│  │  │ /api/    │ │ /api/    │ │ /api/    │ │ /api/stream/ │  │  │
│  │  │portfolio │ │watchlist │ │ chat     │ │ prices (SSE) │  │  │
│  │  └────┬─────┘ └────┬─────┘ └────┬─────┘ └──────┬───────┘  │  │
│  │       │            │            │               │          │  │
│  │  ┌────┴────────────┴────────────┴───────────────┘          │  │
│  │  │                                                         │  │
│  │  │  Shared Services                                        │  │
│  │  │  ├── PriceCache (in-memory, thread-safe) [EXISTS]       │  │
│  │  │  ├── DB module  (aiosqlite connection)   [TO BUILD]     │  │
│  │  │  └── LLM module (LiteLLM client)         [TO BUILD]    │  │
│  │  │                                                         │  │
│  │  └─────────────────────────────────────────────────────────│  │
│  │                                                            │  │
│  │  Background Tasks                                          │  │
│  │  ├── MarketDataSource (simulator or Massive) [EXISTS]      │  │
│  │  └── Portfolio snapshot recorder (every 30s) [TO BUILD]    │  │
│  │                                                            │  │
│  │  Static File Mount: /* → frontend build output             │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌──────────────┐                                                │
│  │  SQLite DB    │  /app/db/finally.db (volume-mounted)          │
│  └──────────────┘                                                │
└──────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│  Browser                                                         │
│                                                                  │
│  Next.js Static Export (React + TypeScript + Tailwind)           │
│  ├── EventSource → /api/stream/prices (SSE)                     │
│  ├── fetch()     → /api/portfolio, /api/watchlist, /api/chat     │
│  ├── Lightweight Charts (canvas-based charting)                  │
│  └── Client-side state (prices, sparkline history, UI)           │
└──────────────────────────────────────────────────────────────────┘
```

## Component Responsibilities

| Component | Responsibility | Communicates With | Status |
|-----------|----------------|-------------------|--------|
| **FastAPI app (main.py)** | Lifespan orchestration, router mounting, static file serving | All backend modules | TO BUILD |
| **Market data subsystem** | Produce live prices from simulator or Massive API | PriceCache (write) | EXISTS |
| **PriceCache** | Thread-safe shared price state with version-based change detection | Market data (write), SSE stream (read), Portfolio API (read), Trade execution (read) | EXISTS |
| **SSE stream router** | Push price events to browser via EventSource | PriceCache (read) | EXISTS |
| **DB module** | SQLite connection management, schema init, seed data, query functions | SQLite file on disk | TO BUILD |
| **Portfolio API router** | Positions, cash, trade execution, history snapshots | DB module, PriceCache | TO BUILD |
| **Watchlist API router** | CRUD for watched tickers | DB module, MarketDataSource (add/remove ticker) | TO BUILD |
| **Chat API router** | Accept user messages, call LLM, auto-execute actions | LLM module, DB module, Portfolio API, Watchlist API | TO BUILD |
| **LLM module** | LiteLLM client, prompt construction, structured output parsing, mock mode | Google Gemini API (external), DB module (context) | TO BUILD |
| **Snapshot background task** | Record portfolio value every 30s and after trades | DB module, PriceCache | TO BUILD |
| **Next.js frontend** | Trading terminal UI, SSE consumption, REST API calls | Backend via /api/* | TO BUILD |

## Recommended Project Structure

### Backend

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py               # FastAPI app, lifespan, router mounting, static files
│   ├── market/               # [EXISTS] Market data subsystem
│   │   ├── __init__.py
│   │   ├── cache.py          # PriceCache
│   │   ├── factory.py        # create_market_data_source()
│   │   ├── interface.py      # MarketDataSource ABC
│   │   ├── massive_client.py # MassiveDataSource
│   │   ├── models.py         # PriceUpdate dataclass
│   │   ├── seed_prices.py    # Default tickers + params
│   │   ├── simulator.py      # SimulatorDataSource (GBM)
│   │   └── stream.py         # SSE router factory
│   ├── db/
│   │   ├── __init__.py       # Export public interface
│   │   ├── connection.py     # aiosqlite connection management
│   │   ├── schema.sql        # CREATE TABLE statements
│   │   ├── seed.py           # Default data insertion
│   │   └── queries.py        # Query functions (or split per domain)
│   ├── api/
│   │   ├── __init__.py
│   │   ├── portfolio.py      # Portfolio + trade routes
│   │   ├── watchlist.py      # Watchlist CRUD routes
│   │   ├── chat.py           # Chat route
│   │   └── health.py         # Health check
│   └── llm/
│       ├── __init__.py
│       ├── client.py         # LiteLLM calls + structured output parsing
│       ├── prompts.py        # System prompt, context formatting
│       ├── schemas.py        # Pydantic models for LLM response
│       └── mock.py           # Deterministic mock responses
├── tests/
│   ├── test_market_*.py      # [EXISTS] 66 tests
│   ├── test_db.py
│   ├── test_portfolio.py
│   ├── test_watchlist.py
│   ├── test_chat.py
│   └── test_llm.py
├── pyproject.toml             # [EXISTS]
└── market_data_demo.py        # [EXISTS] Rich terminal demo
```

### Frontend

```
frontend/
├── src/
│   ├── app/
│   │   ├── layout.tsx        # Root layout with dark theme, header
│   │   └── page.tsx          # Main dashboard page
│   ├── components/
│   │   ├── watchlist/        # Watchlist grid with price flashing
│   │   ├── chart/            # Lightweight Charts wrapper
│   │   ├── portfolio/        # Heatmap, P&L chart, positions table
│   │   ├── trade/            # Trade bar (ticker, quantity, buy/sell)
│   │   ├── chat/             # AI chat panel
│   │   └── common/           # Connection status, sparklines
│   ├── hooks/
│   │   ├── useSSE.ts         # EventSource connection + reconnection
│   │   ├── usePrices.ts      # Price state from SSE
│   │   └── usePortfolio.ts   # Portfolio polling / post-trade refresh
│   ├── lib/
│   │   └── api.ts            # Typed fetch wrappers for /api/*
│   └── types/
│       └── index.ts          # Shared TypeScript interfaces
├── next.config.js            # output: 'export'
├── tailwind.config.ts
├── tsconfig.json
└── package.json
```

### Structure Rationale

- **Backend modules mirror the plan exactly:** `market/`, `db/`, `api/`, `llm/` are the four subsystems. Each is self-contained with its own `__init__.py` exporting public interface.
- **DB queries in one module:** For a single-user SQLite app, a single `queries.py` (or split by domain: `queries_portfolio.py`, `queries_watchlist.py`) is simpler than a full ORM. Raw SQL with parameterized queries is appropriate.
- **LLM module separates concerns:** `client.py` handles the LiteLLM call, `prompts.py` formats the context, `schemas.py` defines Pydantic models for structured output parsing, `mock.py` provides test doubles.
- **Frontend components grouped by feature:** Each panel of the trading terminal is a feature folder. `hooks/` centralizes SSE and data fetching logic. `lib/api.ts` provides typed fetch wrappers so components never construct URLs directly.

## Architectural Patterns

### Pattern 1: FastAPI Lifespan for Orchestration

**What:** Use the `@asynccontextmanager` lifespan to initialize DB, start market data, start background tasks, and tear them all down cleanly.
**When to use:** Always. This is the modern FastAPI pattern (replaces deprecated `on_event`).
**Trade-offs:** Centralizes all startup/shutdown logic in one place, which is clean but means `main.py` must know about every subsystem.

**Example:**
```python
from contextlib import asynccontextmanager
from fastapi import FastAPI

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    db = await init_database("db/finally.db")
    price_cache = PriceCache()
    data_source = create_market_data_source(price_cache)
    watchlist_tickers = await db.get_watchlist_tickers()
    await data_source.start(watchlist_tickers)
    snapshot_task = asyncio.create_task(run_snapshot_loop(db, price_cache))

    # Store in app.state for dependency injection
    app.state.db = db
    app.state.price_cache = price_cache
    app.state.data_source = data_source

    yield

    # Shutdown
    snapshot_task.cancel()
    await data_source.stop()
    await db.close()

app = FastAPI(lifespan=lifespan)
```

**Confidence:** HIGH -- this is the documented FastAPI approach.

### Pattern 2: Router Factory with Dependency Injection

**What:** Each API module exports a factory function that accepts its dependencies and returns an `APIRouter`. No global state.
**When to use:** For every router. The market data subsystem already uses this pattern (`create_stream_router(price_cache)`).
**Trade-offs:** Slightly more boilerplate than FastAPI's `Depends()` for simple cases, but much better for testability and avoids circular imports.

**Example:**
```python
# api/portfolio.py
def create_portfolio_router(db, price_cache: PriceCache) -> APIRouter:
    router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])

    @router.get("")
    async def get_portfolio():
        positions = await db.get_positions()
        # ... enrich with live prices from price_cache
        return portfolio_response

    return router
```

**Confidence:** HIGH -- already proven in the codebase.

### Pattern 3: Synchronous SQLite via aiosqlite (No ORM)

**What:** Use `aiosqlite` for non-blocking SQLite access with raw parameterized SQL. No SQLAlchemy, no ORM.
**When to use:** Single-user demo apps with a simple schema. This project has 6 tables with straightforward CRUD.
**Trade-offs:** Simpler, faster to write, no ORM mapping overhead. Downside is manual SQL, but the schema is small enough that this is a benefit (no abstraction layer to learn).

**Example:**
```python
import aiosqlite

class Database:
    def __init__(self, path: str):
        self._path = path
        self._db: aiosqlite.Connection | None = None

    async def connect(self):
        self._db = await aiosqlite.connect(self._path)
        self._db.row_factory = aiosqlite.Row
        await self._db.execute("PRAGMA journal_mode=WAL")
        await self._db.execute("PRAGMA foreign_keys=ON")

    async def get_positions(self, user_id="default"):
        async with self._db.execute(
            "SELECT * FROM positions WHERE user_id = ?", (user_id,)
        ) as cursor:
            return await cursor.fetchall()
```

**Confidence:** MEDIUM -- aiosqlite is the standard async SQLite library for Python. For this single-user demo, raw SQL is the right call. An ORM would be overengineering.

### Pattern 4: Static File Mounting with SPA Fallback

**What:** Mount the Next.js static export as static files, with a catch-all route that serves `index.html` for client-side routing.
**When to use:** When serving a single-page app from FastAPI on the same origin.
**Trade-offs:** Simple, zero CORS, one container. The catch-all must be mounted last so `/api/*` routes take precedence.

**Example:**
```python
from fastapi.staticfiles import StaticFiles

# Mount API routers first (they take precedence)
app.include_router(portfolio_router)
app.include_router(watchlist_router)
# ...

# Mount static files last -- serves Next.js export
app.mount("/", StaticFiles(directory="static", html=True), name="static")
```

The `html=True` parameter makes StaticFiles serve `index.html` for directory requests, which is the SPA fallback behavior needed for Next.js static exports.

**Confidence:** HIGH -- documented FastAPI pattern.

### Pattern 5: LLM Structured Output with Pydantic Validation

**What:** Define a Pydantic model for the expected LLM response shape, pass its JSON schema to LiteLLM's `response_format`, and validate the response.
**When to use:** For the chat endpoint. Gemini supports structured outputs natively.
**Trade-offs:** Structured output ensures the LLM response is always parseable. The Pydantic model serves as both the schema definition and the response validator.

**Example:**
```python
from pydantic import BaseModel
from litellm import acompletion

class TradeAction(BaseModel):
    ticker: str
    side: str  # "buy" or "sell"
    quantity: float

class WatchlistChange(BaseModel):
    ticker: str
    action: str  # "add" or "remove"

class ChatResponse(BaseModel):
    message: str
    trades: list[TradeAction] = []
    watchlist_changes: list[WatchlistChange] = []

response = await acompletion(
    model="gemini/gemini-3.1-flash-lite-preview",
    messages=messages,
    response_format=ChatResponse,
)
parsed = ChatResponse.model_validate_json(response.choices[0].message.content)
```

**Confidence:** MEDIUM -- LiteLLM supports Pydantic-based `response_format` for Gemini, but the exact `gemini-3.1-flash-lite-preview` model needs verification at build time. The pattern itself is well-documented.

## Data Flow

### 1. Live Price Stream (EXISTS)

```
MarketDataSource (background task, every 500ms)
    ↓ writes
PriceCache (in-memory, version counter bumps)
    ↓ reads (poll every 500ms)
SSE Generator (/api/stream/prices)
    ↓ pushes
Browser EventSource
    ↓ updates
React state → Watchlist prices, sparklines, chart
```

### 2. Trade Execution (TO BUILD)

```
User clicks Buy/Sell (or LLM issues trade)
    ↓
Frontend POST /api/portfolio/trade {ticker, quantity, side}
    ↓
Portfolio router reads current price from PriceCache
    ↓
DB validates: sufficient cash (buy) or shares (sell)
    ↓
DB writes: INSERT trade, UPDATE position, UPDATE cash_balance
    ↓
DB writes: INSERT portfolio_snapshot (immediate post-trade)
    ↓
Returns: {trade, cash_balance, position}
    ↓
Frontend updates positions table, portfolio value, heatmap
```

### 3. LLM Chat with Auto-Execution (TO BUILD)

```
User types message
    ↓
Frontend POST /api/chat {message}
    ↓
Backend loads context:
  ├── Portfolio (DB): cash, positions with current prices (PriceCache)
  ├── Watchlist (DB): tickers with current prices (PriceCache)
  └── History (DB): last 10 chat messages
    ↓
Construct prompt: system + context + history + user message
    ↓
LiteLLM → Gemini (or mock if LLM_MOCK=true)
    ↓
Parse structured response: {message, trades[], watchlist_changes[]}
    ↓
Auto-execute trades (reuse trade execution logic)
Auto-execute watchlist changes (add/remove + MarketDataSource.add_ticker/remove_ticker)
    ↓
Store message + actions in chat_messages table
    ↓
Return complete response to frontend
    ↓
Frontend renders message + inline action confirmations
```

### 4. Portfolio Snapshot (TO BUILD)

```
Background task (every 30s):
    ↓
Read all positions from DB
Read current prices from PriceCache
Calculate total_value = cash + sum(quantity * current_price)
    ↓
INSERT portfolio_snapshot
```

### 5. Watchlist Sync with Market Data Source

```
User adds ticker (manual or via LLM)
    ↓
POST /api/watchlist {ticker}
    ↓
DB: INSERT into watchlist
MarketDataSource.add_ticker(ticker)  ← starts tracking new ticker
    ↓
SSE stream now includes new ticker's prices
    ↓
Frontend sees new ticker in stream, adds to watchlist UI
```

Important: The MarketDataSource tracks the **union** of watchlist tickers and held-position tickers. When a ticker is removed from the watchlist but still held as a position, it must remain tracked for live P&L updates. The watchlist router must coordinate with the data source accordingly.

### State Management Summary

| State | Location | Persistence | Access Pattern |
|-------|----------|-------------|----------------|
| Live prices | PriceCache (server memory) | None (regenerated) | Read by SSE, portfolio, trades |
| Sparkline history | Browser React state | Session only (since page load) | Accumulated from SSE events |
| Positions, cash | SQLite | Persistent (volume mount) | Read/write by API routes |
| Trade history | SQLite | Persistent | Append-only, read for display |
| Portfolio snapshots | SQLite | Persistent | Append by background task + trades, read for P&L chart |
| Chat messages | SQLite | Persistent | Append on each message, read last 10 for LLM context |
| Watchlist | SQLite | Persistent | CRUD by user/LLM |

## Build Order (Dependency Chain)

The components have clear dependencies that dictate build order:

```
Phase 1: Database Layer
    └── No dependencies on other unbuilt components
    └── Everything else depends on this

Phase 2: Portfolio + Watchlist APIs
    └── Depends on: DB layer, PriceCache (exists)
    └── Watchlist API also coordinates with MarketDataSource (exists)

Phase 3: LLM Chat Integration
    └── Depends on: DB layer, Portfolio API (reuse trade logic), Watchlist API
    └── Most complex — builds on top of phases 1 and 2

Phase 4: app/main.py (Lifespan Orchestration)
    └── Depends on: all backend modules existing
    └── Wires everything together

Phase 5: Frontend
    └── Depends on: all API endpoints available
    └── Can be partially developed in parallel with mock APIs

Phase 6: Docker + Scripts
    └── Depends on: both frontend and backend complete

Phase 7: Testing
    └── Unit tests alongside each phase
    └── E2E tests after Docker is working
```

**Critical path:** DB layer is the first bottleneck. Nothing else can be built without it.

**Parallelism opportunity:** Frontend development can begin once API contracts are defined (phases 2-3), using mock responses. However, given this is a course project built by AI agents, sequential is simpler.

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| Google Gemini API | LiteLLM `acompletion()` with structured output | Requires `GOOGLE_API_KEY`. Mock mode (`LLM_MOCK=true`) bypasses. |
| Massive (Polygon.io) API | REST polling via `massive` Python client | Optional. Simulator is default. Already implemented. |

### Internal Boundaries

| Boundary | Communication | Key Consideration |
|----------|---------------|-------------------|
| Frontend <-> Backend | REST (`/api/*`) + SSE (`/api/stream/prices`) | Same origin, no CORS. All types must be consistent. |
| API routes <-> DB | Direct function calls on shared `Database` instance | Passed via `app.state` or router factory injection |
| API routes <-> PriceCache | Direct method calls on shared instance | Read-only from API perspective; writes come from MarketDataSource only |
| Chat route <-> Portfolio/Watchlist | Reuse same trade execution and watchlist functions | Chat auto-execution must go through the same validation as manual actions |
| Watchlist route <-> MarketDataSource | `add_ticker()` / `remove_ticker()` calls | Must handle the union of watchlist + held positions for tracking |
| Snapshot task <-> DB + PriceCache | Reads from both, writes to DB | Runs independently every 30s; also triggered after each trade |

## Anti-Patterns

### Anti-Pattern 1: Global State Instead of Dependency Injection

**What people do:** Store `price_cache`, `db`, etc. as module-level globals imported everywhere.
**Why it's wrong:** Makes testing painful (must monkeypatch globals), creates circular imports, hides dependencies.
**Do this instead:** Use the router factory pattern already established. Pass dependencies through `app.state` or factory function arguments.

### Anti-Pattern 2: SQLAlchemy ORM for a 6-Table Demo App

**What people do:** Set up SQLAlchemy models, sessions, async engine, Alembic migrations for a small schema.
**Why it's wrong:** Massive abstraction overhead for a single-user app with simple CRUD. Adds dependencies, complexity, and a learning curve that provides no value here.
**Do this instead:** Use `aiosqlite` directly with parameterized SQL. The schema is small enough to manage with a single `.sql` file.

### Anti-Pattern 3: Separate Trade Validation for Manual vs LLM Trades

**What people do:** Write trade validation logic twice -- once in the portfolio router and once in the chat handler.
**Why it's wrong:** Leads to inconsistent validation, duplicated bugs, and divergent behavior.
**Do this instead:** Extract trade execution into a shared function that both the portfolio route and the chat auto-executor call. Same validation, same DB writes, same response shape.

### Anti-Pattern 4: WebSocket for Bidirectional Communication

**What people do:** Reach for WebSocket because "real-time = WebSocket."
**Why it's wrong:** This app only needs server-to-client push (prices). Client-to-server is plain REST. WebSocket adds connection management complexity, custom reconnection logic, and protocol handling.
**Do this instead:** SSE for server push (already implemented), REST for client requests. This is already the correct choice.

### Anti-Pattern 5: Polling Portfolio State Instead of Event-Driven Updates

**What people do:** Set up a polling loop on the frontend to refresh portfolio data every N seconds.
**Why it's wrong:** Wasteful and laggy. Portfolio state only changes when a trade executes.
**Do this instead:** Refresh portfolio state on the frontend after each trade response. The only "live" element in the portfolio is current price (from SSE) and total value (computed client-side from positions + SSE prices).

## Scaling Considerations

This is a single-user demo app, so scaling is not a primary concern. But for reference:

| Scale | Architecture Adjustments |
|-------|--------------------------|
| 1 user (target) | Current architecture is perfect. SQLite, in-process everything, no external dependencies. |
| 10 users | SQLite WAL mode handles concurrent reads fine. Would need per-user price cache filtering in SSE. |
| 100+ users | Replace SQLite with PostgreSQL. Move market data to a shared service. SSE per-user filtering becomes important. |

### First Bottleneck

SSE connections. Each connected browser holds an open HTTP connection. Uvicorn with a single worker handles this fine for 1 user. At ~50+ concurrent SSE connections, would need multiple workers or an async-native server.

Not relevant for this project.

## Sources

- [FastAPI Lifespan Events](https://fastapi.tiangolo.com/advanced/events/) -- official docs on lifespan context manager pattern
- [FastAPI Static Files](https://fastapi.tiangolo.com/tutorial/static-files/) -- static file serving with `html=True`
- [LiteLLM Structured Outputs](https://docs.litellm.ai/docs/completion/json_mode) -- JSON mode and structured output with Pydantic
- [LiteLLM Gemini Provider](https://docs.litellm.ai/docs/providers/gemini) -- Gemini integration docs
- [Lightweight Charts Getting Started](https://tradingview.github.io/lightweight-charts/docs) -- TradingView canvas-based charting
- [Next.js Static Exports Guide](https://nextjs.org/docs/pages/guides/static-exports) -- `output: 'export'` configuration
- [aiosqlite on PyPI](https://pypi.org/project/aiosqlite/) -- async SQLite for Python
- [FastAPI Lifespan Explained (Jan 2026)](https://medium.com/algomart/fastapi-lifespan-explained-the-right-way-to-handle-startup-and-shutdown-logic-f825f38dd304) -- modern lifespan patterns

---
*Architecture research for: FinAlly AI Trading Workstation*
*Researched: 2026-03-16*
