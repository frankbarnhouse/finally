# Architecture

**Analysis Date:** 2026-03-16

## Pattern Overview

**Overall:** Monolith — single FastAPI process serves both API and static frontend files on port 8000.

**Key Characteristics:**
- Single Docker container, single port, no inter-service communication
- Backend owns all business logic: database, market data, LLM integration, SSE streaming
- Frontend is a static Next.js export served by FastAPI at the root path
- All frontend API calls go to the same origin (`/api/*`) — zero CORS complexity
- SQLite database initialized lazily on first request (schema + seed data auto-created)

## Layers

**Frontend (static, not yet built):**
- Purpose: Render the trading terminal UI, consume SSE stream, call REST API
- Location: `frontend/` (Next.js project — currently empty, to be built)
- Contains: React components, Tailwind CSS, TypeScript
- Depends on: Backend REST endpoints at `/api/*`, SSE at `/api/stream/prices`
- Used by: End user via browser

**API Layer:**
- Purpose: Route HTTP requests to business logic
- Location: `backend/app/api/` (stub directories exist; routes not yet implemented)
- Contains: FastAPI routers for `chat`, `health`, `portfolio`, `watchlist`
- Depends on: DB layer, market cache, LLM module
- Used by: Frontend

**Market Data Subsystem (complete):**
- Purpose: Produce live price updates from either a GBM simulator or the Massive REST API
- Location: `backend/app/market/`
- Contains: abstract interface, two implementations, shared price cache, SSE router factory
- Depends on: nothing internal (standalone subsystem)
- Used by: SSE streaming endpoint, portfolio valuation, trade execution

**Database Layer (not yet implemented):**
- Purpose: Persist portfolio state, trades, watchlist, chat history, snapshots
- Location: `backend/app/db/` (stub exists in `__pycache__` evidence; no source files yet)
- Contains: schema SQL, seed data, connection management, query functions
- Depends on: SQLite file at `/app/db/finally.db` (runtime path)
- Used by: API routes

**LLM Integration (not yet implemented):**
- Purpose: Chat assistant that can analyze portfolio and execute trades
- Location: `backend/app/llm/` (stub exists in `__pycache__` evidence; no source files yet)
- Contains: LiteLLM client, prompt construction, structured output parsing, mock mode
- Depends on: `GOOGLE_API_KEY` env var, `LLM_MOCK` env var, DB layer, market cache
- Used by: `/api/chat` route

## Data Flow

**Live Price Stream:**

1. Background task (`SimulatorDataSource` or `MassiveDataSource`) runs every 500ms
2. Task calls `PriceCache.update(ticker, price)` for each tracked ticker
3. SSE generator at `/api/stream/prices` polls `price_cache.version` every 500ms
4. When version changes, generator serializes `price_cache.get_all()` and yields SSE event
5. Browser `EventSource` receives event, updates UI with price flash animation

**Trade Execution (planned):**

1. Frontend POSTs `{ticker, quantity, side}` to `/api/portfolio/trade`
2. API route reads current price from `PriceCache.get_price(ticker)`
3. DB layer validates cash/shares, writes trade record, updates position and cash
4. DB layer records `portfolio_snapshot` immediately post-trade
5. API returns updated position and cash balance to frontend

**LLM Chat (planned):**

1. Frontend POSTs user message to `/api/chat`
2. Backend loads portfolio context (from DB) + last 10 chat messages
3. LiteLLM calls `gemini/gemini-3.1-flash-lite-preview` with structured output schema
4. Backend auto-executes any `trades` or `watchlist_changes` in LLM response
5. Backend persists message + executed actions to `chat_messages` table
6. Returns complete JSON response to frontend

**State Management:**
- Server-side: SQLite for persistent state (positions, cash, history, chat)
- Server-side: `PriceCache` (in-memory, no persistence) for live prices
- Client-side: React component state accumulated from SSE events (sparklines, price history)

## Key Abstractions

**MarketDataSource:**
- Purpose: Uniform interface for any price data provider
- Examples: `backend/app/market/interface.py`, `backend/app/market/simulator.py`, `backend/app/market/massive_client.py`
- Pattern: Abstract base class with `start(tickers)`, `stop()`, `add_ticker(ticker)`, `remove_ticker(ticker)`, `get_tickers()` lifecycle methods

**PriceCache:**
- Purpose: Thread-safe shared memory between the background data source and all readers
- Examples: `backend/app/market/cache.py`
- Pattern: Lock-protected dict with monotonic `version` counter for change detection

**PriceUpdate:**
- Purpose: Immutable price snapshot with derived properties for SSE serialization
- Examples: `backend/app/market/models.py`
- Pattern: Frozen dataclass with computed properties (`change`, `change_percent`, `direction`) and `to_dict()` for JSON

**Router Factories (market/stream.py):**
- Purpose: Create FastAPI `APIRouter` instances with injected dependencies (no globals)
- Examples: `backend/app/market/stream.py` — `create_stream_router(price_cache)`
- Pattern: Factory function returns a router; enables dependency injection and clean test isolation

## Entry Points

**Backend Application (not yet created — planned):**
- Location: `backend/app/main.py` (does not exist yet)
- Triggers: `uvicorn app.main:app` from Docker CMD
- Responsibilities: Create FastAPI app, initialize DB, start market data source, mount static files, include all routers

**Market Data Demo:**
- Location: `backend/market_data_demo.py`
- Triggers: `uv run market_data_demo.py`
- Responsibilities: Terminal dashboard demo using Rich, not part of production app

**SSE Stream Router:**
- Location: `backend/app/market/stream.py` — `create_stream_router(price_cache)`
- Triggers: `GET /api/stream/prices` via `EventSource`
- Responsibilities: Long-lived SSE generator that pushes all tracked prices every ~500ms

## Error Handling

**Strategy:** Let exceptions propagate to FastAPI exception handlers for API routes; background tasks catch and log errors to prevent loop termination.

**Patterns:**
- `SimulatorDataSource._run_loop()`: broad `except Exception` with `logger.exception(...)` — loop continues on error
- `MassiveDataSource._poll_once()`: broad `except Exception` with `logger.error(...)` — poll loop retries after interval
- `MassiveDataSource._poll_once()`: narrow `except (AttributeError, TypeError)` for individual snapshot parsing — skips bad entries, logs warning

## Cross-Cutting Concerns

**Logging:** Standard Python `logging` module; `logging.getLogger(__name__)` per module; no centralized configuration yet (planned in `app/main.py`)
**Validation:** FastAPI Pydantic request validation for API routes (not yet implemented); ticker normalization via `.upper().strip()` in market data source methods
**Authentication:** None — single-user app, `user_id` hardcoded to `"default"` in all DB operations

---

*Architecture analysis: 2026-03-16*
