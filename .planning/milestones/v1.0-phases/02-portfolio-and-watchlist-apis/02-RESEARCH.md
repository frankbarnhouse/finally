# Phase 2: Portfolio and Watchlist APIs - Research

**Researched:** 2026-03-16
**Domain:** FastAPI REST endpoints, SQLite transaction handling, async background tasks
**Confidence:** HIGH

## Summary

Phase 2 builds the core trading and watchlist API layer on top of Phase 1's database foundation and the existing market data subsystem. The work involves seven REST endpoints (portfolio CRUD, trade execution, watchlist CRUD, health check) plus a background task for portfolio snapshots. All endpoints are pure FastAPI + aiosqlite -- no new dependencies needed.

The critical technical challenge is trade execution correctness: atomic transactions with `BEGIN IMMEDIATE` to prevent race conditions on cash balance and position updates. The existing codebase establishes clear patterns -- router factory injection (from `stream.py`), `get_db()` singleton, and `PriceCache.get_price()` for current market prices -- that Phase 2 should follow directly.

**Primary recommendation:** Follow the router factory pattern from `app/market/stream.py`. Inject both `PriceCache` and `get_db` into router factories. Use `BEGIN IMMEDIATE` transactions for trade execution. Keep each endpoint handler thin, delegating to service-layer functions for testability.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| PORT-01 | User can view all positions with cash balance and total portfolio value | GET /api/portfolio endpoint; reads positions table + users_profile + PriceCache for live prices |
| PORT-02 | User can execute buy market orders filled at current price | POST /api/portfolio/trade; PriceCache.get_price() for fill price; BEGIN IMMEDIATE transaction |
| PORT-03 | User can execute sell market orders filled at current price | Same endpoint as PORT-02 with side="sell"; update/delete position logic |
| PORT-04 | Trade validation rejects insufficient cash (buy) or insufficient shares (sell) | Validation in service layer before DB writes; return 400 with descriptive error |
| PORT-05 | Selling entire position removes the position row (position returns null) | DELETE FROM positions when quantity reaches 0; response position field is null |
| PORT-06 | Portfolio snapshots recorded every 30s and immediately after each trade | asyncio background task + post-trade snapshot call |
| PORT-07 | User can retrieve portfolio value history for P&L chart | GET /api/portfolio/history; SELECT from portfolio_snapshots ordered by recorded_at |
| WATCH-01 | User can view watchlist tickers with latest prices | GET /api/watchlist; join DB watchlist with PriceCache.get_price() |
| WATCH-02 | User can add a ticker to the watchlist | POST /api/watchlist; INSERT OR IGNORE + MarketDataSource.add_ticker() |
| WATCH-03 | User can remove a ticker from the watchlist | DELETE /api/watchlist/{ticker}; only remove from data source if not held in positions |
| INFRA-04 | Health check endpoint | GET /api/health; returns {"status": "ok"} |
</phase_requirements>

## Standard Stack

### Core (already installed)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | 0.128.7 | REST API framework | Already in project, async-native |
| aiosqlite | 0.22.1 | Async SQLite access | Already used by Phase 1 DB layer |
| uvicorn | >=0.32.0 | ASGI server | Already in project |

### Supporting (already installed)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pydantic (via FastAPI) | bundled | Request/response models | All endpoint input validation and response serialization |
| uuid (stdlib) | - | Trade and snapshot IDs | TEXT PRIMARY KEY generation |
| asyncio (stdlib) | - | Background task for snapshots | 30-second portfolio snapshot loop |

### No New Dependencies Needed

Phase 2 requires zero new packages. FastAPI provides Pydantic for request/response models, aiosqlite handles all DB operations, and PriceCache (already built) provides live prices.

## Architecture Patterns

### Recommended Project Structure
```
backend/app/
  api/                    # currently empty (has __pycache__ only)
    __init__.py
    portfolio.py          # Router factory: create_portfolio_router(cache, data_source)
    watchlist.py          # Router factory: create_watchlist_router(cache, data_source)
    health.py             # Simple router, no dependencies
  services/
    __init__.py
    portfolio.py          # Trade execution, position queries, snapshot logic
    watchlist.py          # Watchlist CRUD operations
  db/                     # Phase 1 (exists)
  market/                 # Existing (exists)
```

### Pattern 1: Router Factory (established pattern)
**What:** Each API module exports a `create_X_router()` function that accepts dependencies and returns a `fastapi.APIRouter`.
**When to use:** Every router that needs PriceCache, MarketDataSource, or DB access.
**Example:**
```python
# Source: established in app/market/stream.py
from fastapi import APIRouter
from app.market import PriceCache, MarketDataSource

def create_portfolio_router(price_cache: PriceCache) -> APIRouter:
    router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])

    @router.get("")
    async def get_portfolio():
        db = await get_db()
        # ... query positions, compute values using price_cache
        ...

    return router
```

### Pattern 2: BEGIN IMMEDIATE Transactions for Trades
**What:** Use `BEGIN IMMEDIATE` to acquire a write lock before reading cash/positions, preventing TOCTOU race conditions.
**When to use:** Trade execution (POST /api/portfolio/trade) only. Read-only endpoints use default transactions.
**Example:**
```python
# aiosqlite supports execute("BEGIN IMMEDIATE") directly
async def execute_trade(db, ticker, side, quantity, price):
    await db.execute("BEGIN IMMEDIATE")
    try:
        # Read cash balance
        cursor = await db.execute(
            "SELECT cash_balance FROM users_profile WHERE id = ?", ("default",)
        )
        row = await cursor.fetchone()
        cash = row[0]

        if side == "buy":
            cost = quantity * price
            if cash < cost:
                await db.execute("ROLLBACK")
                return None, f"Insufficient cash: need ${cost:.2f} but only ${cash:.2f} available"
            # Update cash, upsert position, insert trade
            ...

        await db.execute("COMMIT")
    except Exception:
        await db.execute("ROLLBACK")
        raise
```

### Pattern 3: Service Layer Separation
**What:** Business logic (trade execution, portfolio valuation) in `services/` modules; route handlers in `api/` modules stay thin.
**When to use:** Trade execution logic, portfolio valuation, snapshot recording.
**Why:** Testable without HTTP; service functions can be called from both API routes and the chat/LLM system in Phase 3.

### Pattern 4: Pydantic Models for Request/Response
**What:** Define Pydantic models for all request bodies and response shapes.
**When to use:** Every endpoint.
**Example:**
```python
from pydantic import BaseModel, Field

class TradeRequest(BaseModel):
    ticker: str
    quantity: float = Field(gt=0)
    side: str  # "buy" or "sell"

class TradeResponse(BaseModel):
    trade: dict
    cash_balance: float
    position: dict | None
```

### Anti-Patterns to Avoid
- **Inline SQL in route handlers:** Breaks testability. Keep SQL in service functions.
- **Using PriceCache.get_all() when get_price() suffices:** Don't fetch all prices when you only need one ticker's price.
- **Removing ticker from MarketDataSource on watchlist delete without checking positions:** A ticker removed from the watchlist but still held in positions must continue receiving price updates. Check positions table before calling `data_source.remove_ticker()`.
- **Forgetting ROLLBACK on transaction failure:** Always wrap `BEGIN IMMEDIATE` in try/except with explicit ROLLBACK.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Request validation | Manual if/else checks | Pydantic models with Field constraints | Automatic 422 errors with details |
| UUID generation | Custom ID schemes | `uuid.uuid4()` | Standard, collision-proof |
| ISO timestamps | Manual string formatting | `datetime.now(timezone.utc).isoformat()` | Already used in Phase 1 seed.py |
| Avg cost calculation | - | Weighted average formula inline | Simple math: `(old_qty * old_avg + new_qty * price) / (old_qty + new_qty)` |

## Common Pitfalls

### Pitfall 1: TOCTOU on Cash Balance
**What goes wrong:** Read cash, check sufficiency, then write -- but another request modifies cash between read and write.
**Why it happens:** Default SQLite transactions don't acquire a write lock on read.
**How to avoid:** `BEGIN IMMEDIATE` acquires a reserved lock immediately. Single-writer guarantee in WAL mode.
**Warning signs:** Negative cash balance in testing.

### Pitfall 2: Orphaned Price Tracking After Watchlist Remove
**What goes wrong:** Removing a ticker from the watchlist also removes it from the MarketDataSource/PriceCache, but the user still holds a position in that ticker. Portfolio P&L goes stale.
**Why it happens:** Not checking positions table before removing from data source.
**How to avoid:** On watchlist remove: DELETE from watchlist table, but only call `data_source.remove_ticker()` if the ticker is NOT in the positions table. The PLAN.md explicitly states "The cache tracks the union of watchlist tickers and held-position tickers."
**Warning signs:** Position values showing stale prices after watchlist removal.

### Pitfall 3: Selling More Than Owned
**What goes wrong:** Quantity validation only checks `quantity > 0` but not against current position.
**How to avoid:** In sell path, query position quantity and validate `sell_quantity <= position_quantity` before executing.

### Pitfall 4: Position Upsert on Buy
**What goes wrong:** INSERT fails because position already exists (UNIQUE constraint).
**How to avoid:** Use INSERT ... ON CONFLICT UPDATE pattern, or check existence first within the transaction. The weighted average cost must be recalculated: `new_avg = (old_qty * old_avg + buy_qty * price) / (old_qty + buy_qty)`.

### Pitfall 5: Snapshot Background Task Lifecycle
**What goes wrong:** Background task starts before DB is initialized, or continues after app shutdown.
**How to avoid:** Use FastAPI lifespan events. Start the snapshot task in `lifespan` startup, cancel it in shutdown.

### Pitfall 6: Snapshot Needs All Position Prices
**What goes wrong:** Snapshot calculates total value but some tickers have no price in cache yet (None).
**How to avoid:** Skip tickers with no cached price, or use avg_cost as fallback. Document the choice.

## Code Examples

### Trade Execution - Buy Path
```python
# Core logic for buy trade within BEGIN IMMEDIATE transaction
cost = round(quantity * price, 2)
if cash < cost:
    return error("Insufficient cash: need ${cost:.2f} but only ${cash:.2f} available")

new_cash = round(cash - cost, 2)
await db.execute("UPDATE users_profile SET cash_balance = ? WHERE id = ?", (new_cash, user_id))

# Upsert position with weighted average cost
cursor = await db.execute(
    "SELECT quantity, avg_cost FROM positions WHERE user_id = ? AND ticker = ?",
    (user_id, ticker),
)
existing = await cursor.fetchone()

if existing:
    old_qty, old_avg = existing[0], existing[1]
    new_qty = old_qty + quantity
    new_avg = round((old_qty * old_avg + quantity * price) / new_qty, 2)
    await db.execute(
        "UPDATE positions SET quantity = ?, avg_cost = ?, updated_at = ? WHERE user_id = ? AND ticker = ?",
        (new_qty, new_avg, now, user_id, ticker),
    )
else:
    await db.execute(
        "INSERT INTO positions (user_id, ticker, quantity, avg_cost, updated_at) VALUES (?, ?, ?, ?, ?)",
        (user_id, ticker, quantity, price, now),
    )
```

### Trade Execution - Sell Path
```python
# Core logic for sell trade
cursor = await db.execute(
    "SELECT quantity, avg_cost FROM positions WHERE user_id = ? AND ticker = ?",
    (user_id, ticker),
)
existing = await cursor.fetchone()
if not existing or existing[0] < quantity:
    owned = existing[0] if existing else 0
    return error(f"Insufficient shares: want to sell {quantity} but only own {owned}")

proceeds = round(quantity * price, 2)
new_cash = round(cash + proceeds, 2)
await db.execute("UPDATE users_profile SET cash_balance = ? WHERE id = ?", (new_cash, user_id))

remaining = existing[0] - quantity
if remaining == 0:
    await db.execute(
        "DELETE FROM positions WHERE user_id = ? AND ticker = ?", (user_id, ticker)
    )
    position_result = None
else:
    await db.execute(
        "UPDATE positions SET quantity = ?, updated_at = ? WHERE user_id = ? AND ticker = ?",
        (remaining, now, user_id, ticker),
    )
    position_result = {"ticker": ticker, "quantity": remaining, "avg_cost": existing[1]}
```

### Portfolio Snapshot Background Task
```python
import asyncio
import uuid
from datetime import datetime, timezone

async def snapshot_loop(price_cache, interval: float = 30.0):
    """Record portfolio value every `interval` seconds."""
    while True:
        await asyncio.sleep(interval)
        await record_snapshot(price_cache)

async def record_snapshot(price_cache):
    """Calculate and store current portfolio total value."""
    db = await get_db()
    user_id = "default"
    cursor = await db.execute(
        "SELECT cash_balance FROM users_profile WHERE id = ?", (user_id,)
    )
    row = await cursor.fetchone()
    cash = row[0]

    cursor = await db.execute(
        "SELECT ticker, quantity FROM positions WHERE user_id = ?", (user_id,)
    )
    positions = await cursor.fetchall()

    total = cash
    for pos in positions:
        price = price_cache.get_price(pos[0])
        if price is not None:
            total += pos[1] * price

    now = datetime.now(timezone.utc).isoformat()
    await db.execute(
        "INSERT INTO portfolio_snapshots (id, user_id, total_value, recorded_at) VALUES (?, ?, ?, ?)",
        (str(uuid.uuid4()), user_id, round(total, 2), now),
    )
    await db.commit()
```

### Watchlist Add with Data Source Sync
```python
async def add_to_watchlist(db, ticker, data_source):
    """Add ticker to watchlist and start tracking prices."""
    now = datetime.now(timezone.utc).isoformat()
    await db.execute(
        "INSERT OR IGNORE INTO watchlist (user_id, ticker, added_at) VALUES (?, ?, ?)",
        ("default", ticker.upper(), now),
    )
    await db.commit()
    await data_source.add_ticker(ticker.upper())
```

### Health Check
```python
def create_health_router() -> APIRouter:
    router = APIRouter(prefix="/api", tags=["system"])

    @router.get("/health")
    async def health():
        return {"status": "ok"}

    return router
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Depends(get_db) injection | Router factory with get_db() call inside handler | Current project pattern | Consistent with market data module |
| SQLAlchemy ORM | Raw aiosqlite queries | Project decision | Simpler, no ORM overhead for 6 tables |
| Separate migration tool | CREATE TABLE IF NOT EXISTS | Project decision | Lazy init, zero-config |

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.3+ with pytest-asyncio 0.24+ |
| Config file | `backend/pyproject.toml` [tool.pytest.ini_options] |
| Quick run command | `cd backend && uv run --extra dev pytest tests/ -x -q` |
| Full suite command | `cd backend && uv run --extra dev pytest -v` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PORT-01 | GET /api/portfolio returns positions, cash, total value | unit | `cd backend && uv run --extra dev pytest tests/api/test_portfolio.py::test_get_portfolio -x` | No - Wave 0 |
| PORT-02 | Buy trade deducts cash, creates/updates position | unit | `cd backend && uv run --extra dev pytest tests/api/test_portfolio.py::test_buy_trade -x` | No - Wave 0 |
| PORT-03 | Sell trade adds cash, updates position | unit | `cd backend && uv run --extra dev pytest tests/api/test_portfolio.py::test_sell_trade -x` | No - Wave 0 |
| PORT-04 | Insufficient cash/shares returns 400 | unit | `cd backend && uv run --extra dev pytest tests/api/test_portfolio.py::test_trade_validation -x` | No - Wave 0 |
| PORT-05 | Full sell removes position row | unit | `cd backend && uv run --extra dev pytest tests/api/test_portfolio.py::test_sell_closes_position -x` | No - Wave 0 |
| PORT-06 | Snapshots recorded periodically and after trade | unit | `cd backend && uv run --extra dev pytest tests/services/test_portfolio.py::test_snapshot -x` | No - Wave 0 |
| PORT-07 | GET /api/portfolio/history returns snapshots | unit | `cd backend && uv run --extra dev pytest tests/api/test_portfolio.py::test_portfolio_history -x` | No - Wave 0 |
| WATCH-01 | GET /api/watchlist returns tickers with prices | unit | `cd backend && uv run --extra dev pytest tests/api/test_watchlist.py::test_get_watchlist -x` | No - Wave 0 |
| WATCH-02 | POST /api/watchlist adds ticker | unit | `cd backend && uv run --extra dev pytest tests/api/test_watchlist.py::test_add_ticker -x` | No - Wave 0 |
| WATCH-03 | DELETE /api/watchlist/{ticker} removes ticker | unit | `cd backend && uv run --extra dev pytest tests/api/test_watchlist.py::test_remove_ticker -x` | No - Wave 0 |
| INFRA-04 | GET /api/health returns ok | unit | `cd backend && uv run --extra dev pytest tests/api/test_health.py -x` | No - Wave 0 |

### Sampling Rate
- **Per task commit:** `cd backend && uv run --extra dev pytest tests/ -x -q`
- **Per wave merge:** `cd backend && uv run --extra dev pytest -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `backend/tests/api/__init__.py` -- test package init
- [ ] `backend/tests/api/test_portfolio.py` -- covers PORT-01 through PORT-05, PORT-07
- [ ] `backend/tests/api/test_watchlist.py` -- covers WATCH-01, WATCH-02, WATCH-03
- [ ] `backend/tests/api/test_health.py` -- covers INFRA-04
- [ ] `backend/tests/services/__init__.py` -- test package init
- [ ] `backend/tests/services/test_portfolio.py` -- covers PORT-06 snapshot logic
- [ ] Test fixtures: shared `db` fixture (already in tests/db/test_init.py, needs shared conftest), mock PriceCache fixture

### Testing Strategy Notes
- Use FastAPI `TestClient` (via `httpx.AsyncClient`) for endpoint tests
- Mock PriceCache with preset prices for deterministic tests
- Use `tmp_path` + monkeypatch DB_PATH pattern from Phase 1 tests
- Test trade execution at the service layer (no HTTP) for thorough edge case coverage

## Open Questions

1. **Float precision for cash and quantities**
   - What we know: Schema uses REAL (SQLite float). Python floats are IEEE 754.
   - What's unclear: Whether cumulative rounding errors matter for a demo app.
   - Recommendation: Use `round(value, 2)` on all monetary calculations. Acceptable for a demo -- not a real trading system.

2. **Watchlist add: should we validate ticker symbols?**
   - What we know: PLAN.md doesn't mention ticker validation. The simulator has seed prices for 10 tickers.
   - What's unclear: What happens if user adds "INVALID_TICKER" -- simulator won't generate prices for it.
   - Recommendation: Accept any string, uppercase it. The simulator/Massive client will handle unknown tickers (simulator can generate from defaults, Massive will return no data). Keep it simple per CLAUDE.md guidance.

3. **MarketDataSource access pattern**
   - What we know: `create_market_data_source(cache)` returns the source. Watchlist add/remove needs to call `add_ticker()`/`remove_ticker()` on it.
   - What's unclear: Where the data source instance lives in the app lifecycle.
   - Recommendation: Store it in module-level state alongside PriceCache, inject into router factories. The main app startup (when it exists) creates both and passes them in.

## Sources

### Primary (HIGH confidence)
- Existing codebase: `backend/app/market/stream.py` -- router factory pattern
- Existing codebase: `backend/app/market/cache.py` -- PriceCache API
- Existing codebase: `backend/app/db/connection.py` -- get_db() singleton pattern
- Existing codebase: `backend/app/db/schema.py` -- table definitions
- Project PLAN.md -- API contracts, response shapes, trade execution rules

### Secondary (MEDIUM confidence)
- aiosqlite documentation -- BEGIN IMMEDIATE transaction support
- FastAPI documentation -- TestClient, lifespan events, Pydantic integration

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- zero new dependencies, all libraries already in project
- Architecture: HIGH -- follows established patterns from Phase 1 and market data module
- Pitfalls: HIGH -- trade execution edge cases well-understood from PLAN.md spec
- Validation: HIGH -- pytest + pytest-asyncio already configured and working

**Research date:** 2026-03-16
**Valid until:** 2026-04-16 (stable -- no external dependencies to go stale)
