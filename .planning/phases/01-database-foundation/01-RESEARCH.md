# Phase 1: Database Foundation - Research

**Researched:** 2026-03-16
**Domain:** SQLite async persistence with aiosqlite + FastAPI
**Confidence:** HIGH

## Summary

This phase creates the SQLite persistence layer for FinAlly. The domain is well-understood: aiosqlite wraps Python's sqlite3 module with async/await, WAL mode enables concurrent reads during writes, and lazy initialization on first use eliminates migration tooling. The existing backend already has a clean module pattern (see `app/market/`) that the database module should follow.

The primary challenge is designing the initialization flow so it is thread-safe, idempotent, and runs exactly once per process lifetime. The secondary challenge is configuring SQLite pragmas (WAL, busy_timeout) correctly on every connection, since these are per-connection settings.

**Primary recommendation:** Use aiosqlite 0.22.x with a module-level singleton pattern for the database connection, initialized lazily on first access. Set WAL mode and busy_timeout via PRAGMAs immediately after connection. Follow the router factory pattern already established in `app/market/stream.py`.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| DB-01 | SQLite database auto-creates schema and seeds default data on first request (lazy init) | Lazy init pattern with `aiosqlite.connect()` + `CREATE TABLE IF NOT EXISTS` + seed check |
| DB-02 | Default user profile created with $10,000 cash balance | INSERT into users_profile during seed step |
| DB-03 | Default watchlist seeded with 10 tickers | INSERT into watchlist during seed step; tickers match `app/market/seed_prices.py` |
| DB-04 | WAL mode and busy_timeout configured at database initialization | PRAGMA journal_mode=WAL and PRAGMA busy_timeout=5000 set on every connection open |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| aiosqlite | 0.22.1 | Async SQLite wrapper | Only maintained async SQLite library for Python; mirrors sqlite3 API |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| sqlite3 | stdlib | Underlying SQLite engine | Used indirectly via aiosqlite; no separate install |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| aiosqlite | databases + SQLAlchemy | Massive overkill for single-file SQLite; adds ORM complexity |
| aiosqlite | raw sqlite3 in executor | aiosqlite already does this properly with queue-based threading |

**Installation:**
```bash
cd backend && uv add "aiosqlite>=0.22.0"
```

**Version verification:** aiosqlite 0.22.1 is the latest on PyPI (released 2025-12-23). Python >=3.9 required; project uses 3.12.

## Architecture Patterns

### Recommended Project Structure
```
app/
├── market/          # Existing market data subsystem
├── db/              # NEW: Database subsystem
│   ├── __init__.py  # Public API exports (get_db, init_db)
│   ├── connection.py # Connection management, lazy init, pragma config
│   ├── schema.py    # CREATE TABLE statements
│   └── seed.py      # Default data insertion
└── __init__.py
```

### Pattern 1: Lazy Singleton Connection
**What:** A module-level async function that returns a shared database connection, creating it (and the schema/seed data) on first call.
**When to use:** Application startup or first request.
**Example:**
```python
import aiosqlite

_db: aiosqlite.Connection | None = None

async def get_db() -> aiosqlite.Connection:
    """Return the shared database connection, initializing on first call."""
    global _db
    if _db is None:
        _db = await aiosqlite.connect("db/finally.db")
        _db.row_factory = aiosqlite.Row
        await _db.execute("PRAGMA journal_mode=WAL")
        await _db.execute("PRAGMA busy_timeout=5000")
        await _init_schema(_db)
        await _seed_defaults(_db)
    return _db
```

### Pattern 2: Router Factory (Existing Pattern)
**What:** Functions like `create_X_router(db)` that accept dependencies and return FastAPI routers.
**When to use:** All future API modules (watchlist, portfolio, chat) will receive the db connection this way.
**Example:**
```python
# Follows the same pattern as create_stream_router(price_cache)
def create_watchlist_router(db: aiosqlite.Connection) -> APIRouter:
    router = APIRouter(prefix="/api/watchlist", tags=["watchlist"])
    # ... route definitions using db ...
    return router
```

### Pattern 3: Idempotent Schema Creation
**What:** Use `CREATE TABLE IF NOT EXISTS` for all tables so initialization is safe to run multiple times.
**When to use:** Always -- the lazy init may be called on every startup against an existing database file.
**Example:**
```python
SCHEMA = """
CREATE TABLE IF NOT EXISTS users_profile (
    id TEXT PRIMARY KEY DEFAULT 'default',
    cash_balance REAL NOT NULL DEFAULT 10000.0,
    created_at TEXT NOT NULL
);
"""
# Execute with executescript for multiple statements
```

### Pattern 4: Seed Data with Conflict Handling
**What:** Use `INSERT OR IGNORE` for seed data so re-initialization does not duplicate or overwrite existing data.
**When to use:** Seed step after schema creation.
**Example:**
```python
await db.execute(
    "INSERT OR IGNORE INTO users_profile (id, cash_balance, created_at) VALUES (?, ?, ?)",
    ("default", 10000.0, datetime.now(timezone.utc).isoformat()),
)
```

### Anti-Patterns to Avoid
- **Multiple connection instances:** aiosqlite uses a single thread per connection. Creating many connections adds thread overhead and complicates WAL. Use one shared connection.
- **Forgetting to commit:** aiosqlite (like sqlite3) does not auto-commit by default. Every write must be followed by `await db.commit()`.
- **Setting PRAGMAs inside transactions:** `PRAGMA journal_mode=WAL` must be executed outside a transaction. aiosqlite's `isolation_level` defaults to deferred transactions, so execute PRAGMAs right after connect before any other operations.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Async SQLite access | Thread pool executor wrapper | aiosqlite | Already handles queue-based single-thread access correctly |
| UUID generation | Custom ID generation | Python `uuid.uuid4()` | Standard, collision-free, no dependency |
| ISO timestamps | Manual string formatting | `datetime.now(timezone.utc).isoformat()` | Stdlib, consistent format |

**Key insight:** The database layer for this phase is intentionally simple. No ORM, no migration framework, no connection pooling. SQLite + aiosqlite + raw SQL is the right level of abstraction for a single-user demo app.

## Common Pitfalls

### Pitfall 1: WAL Mode Not Persisting Across Connections
**What goes wrong:** Developer sets WAL mode once and assumes it persists. It does persist in the database file, but busy_timeout does NOT persist -- it must be set on every connection.
**Why it happens:** WAL is a database-level setting (persists in file), but busy_timeout is a connection-level setting.
**How to avoid:** Set both PRAGMAs every time a connection is opened, even if WAL is already enabled. This is idempotent and harmless.
**Warning signs:** "database is locked" errors under concurrent async operations.

### Pitfall 2: Forgetting await db.commit()
**What goes wrong:** Data appears to be written during the session but is lost on restart.
**Why it happens:** aiosqlite (like sqlite3) uses implicit transactions. Writes are buffered until commit.
**How to avoid:** Always `await db.commit()` after INSERT/UPDATE/DELETE operations.
**Warning signs:** Data visible during runtime but missing after restart.

### Pitfall 3: Schema SQL Errors Silent in executescript
**What goes wrong:** A typo in one CREATE TABLE statement silently fails when using `executescript`.
**Why it happens:** `executescript` commits any pending transaction first, then executes statements. Errors may be masked.
**How to avoid:** Execute each CREATE TABLE separately with `await db.execute()`, or use `await db.executescript()` and verify table count afterward.
**Warning signs:** Missing tables at runtime, KeyError on column access.

### Pitfall 4: Row Factory Not Set
**What goes wrong:** Query results return tuples instead of dict-like Row objects, making code brittle to column ordering.
**Why it happens:** Default row_factory is None (returns tuples).
**How to avoid:** Set `db.row_factory = aiosqlite.Row` immediately after connection.
**Warning signs:** Accessing results by integer index instead of column name.

### Pitfall 5: Seed Data Overwrites User Changes
**What goes wrong:** Re-initialization (e.g., after container restart with existing volume) resets user's cash balance to $10,000.
**Why it happens:** Using INSERT OR REPLACE instead of INSERT OR IGNORE for seed data.
**How to avoid:** Use `INSERT OR IGNORE` -- only inserts if the row does not already exist.
**Warning signs:** Portfolio resets after container restart.

## Code Examples

### Complete Lazy Init Pattern
```python
import aiosqlite
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path("db/finally.db")

_db: aiosqlite.Connection | None = None

async def get_db() -> aiosqlite.Connection:
    global _db
    if _db is None:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        _db = await aiosqlite.connect(str(DB_PATH))
        _db.row_factory = aiosqlite.Row
        await _db.execute("PRAGMA journal_mode=WAL")
        await _db.execute("PRAGMA busy_timeout=5000")
        await _init_schema(_db)
        await _seed_defaults(_db)
    return _db

async def close_db():
    global _db
    if _db is not None:
        await _db.close()
        _db = None
```

### Schema Creation
```python
TABLES = [
    """CREATE TABLE IF NOT EXISTS users_profile (
        id TEXT PRIMARY KEY DEFAULT 'default',
        cash_balance REAL NOT NULL DEFAULT 10000.0,
        created_at TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS watchlist (
        user_id TEXT NOT NULL DEFAULT 'default',
        ticker TEXT NOT NULL,
        added_at TEXT NOT NULL,
        UNIQUE(user_id, ticker)
    )""",
    """CREATE TABLE IF NOT EXISTS positions (
        user_id TEXT NOT NULL DEFAULT 'default',
        ticker TEXT NOT NULL,
        quantity REAL NOT NULL,
        avg_cost REAL NOT NULL,
        updated_at TEXT NOT NULL,
        UNIQUE(user_id, ticker)
    )""",
    """CREATE TABLE IF NOT EXISTS trades (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL DEFAULT 'default',
        ticker TEXT NOT NULL,
        side TEXT NOT NULL CHECK(side IN ('buy', 'sell')),
        quantity REAL NOT NULL,
        price REAL NOT NULL,
        executed_at TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS portfolio_snapshots (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL DEFAULT 'default',
        total_value REAL NOT NULL,
        recorded_at TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS chat_messages (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL DEFAULT 'default',
        role TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
        content TEXT NOT NULL,
        actions TEXT,
        created_at TEXT NOT NULL
    )""",
]

async def _init_schema(db: aiosqlite.Connection):
    for table_sql in TABLES:
        await db.execute(table_sql)
    await db.commit()
```

### Seed Defaults
```python
DEFAULT_TICKERS = ["AAPL", "GOOGL", "MSFT", "AMZN", "TSLA", "NVDA", "META", "JPM", "V", "NFLX"]

async def _seed_defaults(db: aiosqlite.Connection):
    now = datetime.now(timezone.utc).isoformat()

    # Seed user profile
    await db.execute(
        "INSERT OR IGNORE INTO users_profile (id, cash_balance, created_at) VALUES (?, ?, ?)",
        ("default", 10000.0, now),
    )

    # Seed watchlist
    for ticker in DEFAULT_TICKERS:
        await db.execute(
            "INSERT OR IGNORE INTO watchlist (user_id, ticker, added_at) VALUES (?, ?, ?)",
            ("default", ticker, now),
        )

    await db.commit()
```

### Querying with Row Factory
```python
async def get_watchlist(db: aiosqlite.Connection, user_id: str = "default") -> list[dict]:
    async with db.execute(
        "SELECT ticker, added_at FROM watchlist WHERE user_id = ?", (user_id,)
    ) as cursor:
        rows = await cursor.fetchall()
        return [{"ticker": row["ticker"], "added_at": row["added_at"]} for row in rows]
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| sqlite3 in thread executor | aiosqlite 0.22.x | Stable since 2023 | Clean async/await, no manual threading |
| Alembic migrations | CREATE TABLE IF NOT EXISTS | N/A (project choice) | No migration tooling needed for demo app |
| Connection pooling (aiosqlite-pool) | Single shared connection | N/A (project choice) | Single-user app; one connection is sufficient |

**Deprecated/outdated:**
- aiosqlite < 0.20: Older versions had issues with Python 3.12 compatibility. Use 0.22.x.

## Open Questions

1. **Database file path configuration**
   - What we know: PLAN.md specifies `db/finally.db` relative to project root, mounted as `/app/db` in Docker
   - What's unclear: Whether the path should be configurable via environment variable or hardcoded
   - Recommendation: Hardcode `db/finally.db` for simplicity (matches PLAN.md). The Docker volume mount handles the persistence concern.

2. **Connection lifecycle in FastAPI**
   - What we know: FastAPI has lifespan events for startup/shutdown
   - What's unclear: Whether to init DB in lifespan startup or truly lazily on first request
   - Recommendation: Use FastAPI lifespan to call `get_db()` on startup and `close_db()` on shutdown. This ensures the DB is ready before the first request and properly closed on shutdown.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.3+ with pytest-asyncio 0.24+ |
| Config file | `backend/pyproject.toml` ([tool.pytest.ini_options]) |
| Quick run command | `cd backend && uv run --extra dev pytest tests/db/ -x -v` |
| Full suite command | `cd backend && uv run --extra dev pytest -v` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DB-01 | Schema auto-creates 6 tables on first connect | unit | `cd backend && uv run --extra dev pytest tests/db/test_init.py::test_schema_creates_all_tables -x` | No - Wave 0 |
| DB-02 | Default user profile with $10k cash | unit | `cd backend && uv run --extra dev pytest tests/db/test_init.py::test_default_user_profile -x` | No - Wave 0 |
| DB-03 | Default watchlist has 10 tickers | unit | `cd backend && uv run --extra dev pytest tests/db/test_init.py::test_default_watchlist -x` | No - Wave 0 |
| DB-04 | WAL mode and busy_timeout configured | unit | `cd backend && uv run --extra dev pytest tests/db/test_init.py::test_wal_mode_and_busy_timeout -x` | No - Wave 0 |

### Sampling Rate
- **Per task commit:** `cd backend && uv run --extra dev pytest tests/db/ -x -v`
- **Per wave merge:** `cd backend && uv run --extra dev pytest -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/db/__init__.py` -- package init
- [ ] `tests/db/test_init.py` -- covers DB-01, DB-02, DB-03, DB-04
- [ ] Tests should use tmp_path fixture for isolated SQLite files (no shared state between tests)

## Sources

### Primary (HIGH confidence)
- [PyPI aiosqlite 0.22.1](https://pypi.org/project/aiosqlite/) - version, Python support, API overview
- [aiosqlite official docs](https://aiosqlite.omnilib.dev/en/stable/) - connection API, row_factory, context managers
- [SQLite PRAGMA reference](https://www.sqlite.org/pragma.html) - journal_mode, busy_timeout behavior
- [SQLite WAL documentation](https://sqlite.org/wal.html) - WAL mode semantics and persistence

### Secondary (MEDIUM confidence)
- [Simon Willison: Enabling WAL mode](https://til.simonwillison.net/sqlite/enabling-wal-mode) - WAL mode configuration patterns
- [Bert Hubert: SQLite busy_timeout](https://berthub.eu/articles/posts/a-brief-post-on-sqlite3-database-locked-despite-timeout/) - busy_timeout per-connection behavior

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - aiosqlite is the established async SQLite library; version verified on PyPI
- Architecture: HIGH - patterns derived from existing codebase (market module) and SQLite official docs
- Pitfalls: HIGH - well-documented SQLite gotchas verified across multiple sources

**Research date:** 2026-03-16
**Valid until:** 2026-04-16 (stable domain, unlikely to change)
