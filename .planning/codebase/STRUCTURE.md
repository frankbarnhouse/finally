# Codebase Structure

**Analysis Date:** 2026-03-16

## Directory Layout

```
udemy_finally/                    # Project root
├── backend/                      # FastAPI uv project (Python)
│   ├── app/                      # Application package
│   │   ├── __init__.py
│   │   ├── market/               # Market data subsystem (COMPLETE)
│   │   │   ├── __init__.py       # Public API exports
│   │   │   ├── interface.py      # Abstract MarketDataSource base class
│   │   │   ├── models.py         # PriceUpdate dataclass
│   │   │   ├── cache.py          # PriceCache (thread-safe in-memory store)
│   │   │   ├── factory.py        # create_market_data_source() factory
│   │   │   ├── simulator.py      # GBMSimulator + SimulatorDataSource
│   │   │   ├── massive_client.py # MassiveDataSource (Polygon.io REST polling)
│   │   │   ├── stream.py         # create_stream_router() SSE factory
│   │   │   └── seed_prices.py    # Starting prices + GBM params for default tickers
│   │   ├── api/                  # REST API routers (TO BE BUILT)
│   │   │   ├── chat.py           # POST /api/chat
│   │   │   ├── health.py         # GET /api/health
│   │   │   ├── portfolio.py      # GET/POST /api/portfolio/*
│   │   │   └── watchlist.py      # GET/POST/DELETE /api/watchlist
│   │   ├── db/                   # Database layer (TO BE BUILT)
│   │   │   ├── connection.py     # SQLite connection management
│   │   │   ├── schema.py         # CREATE TABLE statements + lazy init
│   │   │   ├── seed.py           # Default data (user profile, watchlist)
│   │   │   └── queries.py        # All SQL queries as functions
│   │   ├── llm/                  # LLM integration (TO BE BUILT)
│   │   │   ├── chat.py           # LiteLLM client, structured output parsing
│   │   │   ├── mock.py           # Deterministic mock responses (LLM_MOCK=true)
│   │   │   └── prompts.py        # System prompt and context construction
│   │   ├── main.py               # FastAPI app, startup/shutdown (TO BE BUILT)
│   │   └── trade.py              # Trade execution logic (partial — in __pycache__)
│   ├── tests/                    # pytest test suite
│   │   ├── conftest.py           # Root fixtures
│   │   ├── market/               # Market data tests (COMPLETE)
│   │   │   ├── test_cache.py
│   │   │   ├── test_factory.py
│   │   │   ├── test_massive.py
│   │   │   ├── test_models.py
│   │   │   ├── test_simulator.py
│   │   │   └── test_simulator_source.py
│   │   ├── api/                  # API route tests (stub — TO BE BUILT)
│   │   ├── db/                   # Database tests (stub — TO BE BUILT)
│   │   └── llm/                  # LLM tests (stub — TO BE BUILT)
│   ├── market_data_demo.py       # Interactive terminal demo (dev only)
│   ├── pyproject.toml            # uv project config, pytest config, ruff config
│   └── uv.lock                   # Pinned dependency lockfile
├── frontend/                     # Next.js TypeScript project (NOT YET CREATED)
├── test/                         # E2E Playwright tests (NOT YET CREATED)
│   └── node_modules/             # playwright installed (stub)
├── planning/                     # Agent documentation
│   ├── PLAN.md                   # Master project specification
│   ├── MARKET_DATA_SUMMARY.md    # Completed market data component summary
│   ├── MASSIVE_API.md            # Massive API reference
│   └── archive/                  # Historical planning docs
├── .planning/                    # GSD agent outputs
│   └── codebase/                 # Codebase analysis documents
├── .github/
│   └── workflows/                # CI: claude-code-review.yml, claude.yml
├── db/                           # Runtime SQLite volume mount target
│   └── .gitkeep                  # Dir exists in repo; finally.db is gitignored
├── scripts/                      # Start/stop Docker scripts (TO BE CREATED)
├── .env                          # Local secrets (gitignored)
├── .env.example                  # Template for required env vars (to be created)
├── Dockerfile                    # Multi-stage build: Node → Python (TO BE CREATED)
├── CLAUDE.md                     # Project-level agent instructions
└── README.md
```

## Directory Purposes

**`backend/app/market/`:**
- Purpose: Self-contained market data subsystem — the only complete module
- Contains: Abstract interface, GBM simulator, Massive REST client, thread-safe price cache, SSE router factory
- Key files: `interface.py` (contract), `cache.py` (shared state), `stream.py` (SSE endpoint), `factory.py` (env-driven selection)

**`backend/app/api/`:**
- Purpose: FastAPI routers for all REST endpoints
- Contains: One file per resource group — chat, health, portfolio, watchlist
- Key files: `portfolio.py` (trade execution + P&L), `watchlist.py` (CRUD + market data integration)
- Note: Directory exists (evidenced by `__pycache__`) but source files not yet present

**`backend/app/db/`:**
- Purpose: SQLite database layer — connection, schema initialization, all queries
- Contains: Schema definitions, lazy init logic, seed data, query functions
- Note: Directory exists (evidenced by `__pycache__`) but source files not yet present

**`backend/app/llm/`:**
- Purpose: LiteLLM integration for the AI chat assistant
- Contains: Client wrapper, structured output schema, prompt construction, mock mode
- Note: Directory exists (evidenced by `__pycache__`) but source files not yet present

**`backend/tests/`:**
- Purpose: pytest test suite, mirroring `app/` structure
- Contains: One subdirectory per app module; `conftest.py` files for shared fixtures
- Note: Only `tests/market/` has actual test files; `api/`, `db/`, `llm/` are empty stubs

**`db/`:**
- Purpose: Docker volume mount target for SQLite persistence
- Generated: Yes (finally.db created at runtime)
- Committed: No (only `.gitkeep`)

**`planning/`:**
- Purpose: Project-wide documentation for agent coordination
- Contains: Master plan, completed component summaries, reference docs
- Generated: No
- Committed: Yes

**`test/`:**
- Purpose: Playwright E2E tests with separate docker-compose infrastructure
- Contains: Only Playwright node_modules so far; test files not yet written

## Key File Locations

**Entry Points:**
- `backend/app/main.py`: FastAPI app factory (TO BE CREATED — currently does not exist)
- `backend/market_data_demo.py`: Dev demo script, not production

**Configuration:**
- `backend/pyproject.toml`: Python deps, pytest config, ruff lint config
- `backend/uv.lock`: Pinned lockfile
- `.env`: Runtime secrets (gitignored)

**Core Logic (complete):**
- `backend/app/market/interface.py`: `MarketDataSource` abstract contract
- `backend/app/market/cache.py`: `PriceCache` — central shared price state
- `backend/app/market/simulator.py`: `GBMSimulator` + `SimulatorDataSource`
- `backend/app/market/massive_client.py`: `MassiveDataSource` (Polygon.io)
- `backend/app/market/stream.py`: SSE endpoint factory

**Core Logic (planned):**
- `backend/app/main.py`: App entrypoint, lifespan events, router mounting
- `backend/app/db/schema.py`: Schema + lazy init
- `backend/app/db/queries.py`: All SQL query functions
- `backend/app/trade.py`: Trade execution business logic (referenced in `__pycache__`)
- `backend/app/llm/chat.py`: LLM client + structured output handler

**Testing:**
- `backend/tests/market/`: Six test files covering the complete market data subsystem
- `backend/tests/conftest.py`: Root-level pytest fixtures (currently empty)

## Naming Conventions

**Files:**
- snake_case for all Python modules: `massive_client.py`, `seed_prices.py`, `stream.py`
- Prefix `test_` for all test files: `test_cache.py`, `test_simulator.py`
- Descriptive names matching the class/function inside: `interface.py` contains `MarketDataSource`

**Directories:**
- Lowercase, single-word or short noun: `market/`, `api/`, `db/`, `llm/`
- Test directories mirror source directories: `tests/market/` mirrors `app/market/`

**Classes:**
- PascalCase: `PriceCache`, `MarketDataSource`, `SimulatorDataSource`, `MassiveDataSource`, `GBMSimulator`
- Suffix `DataSource` for `MarketDataSource` implementations
- Suffix `Router` not used — factory functions (`create_stream_router`) return `APIRouter`

**Functions:**
- snake_case: `create_market_data_source`, `create_stream_router`, `get_price`
- Factory functions prefixed `create_`: `create_market_data_source()`, `create_stream_router()`

## Where to Add New Code

**New REST API route group (e.g., portfolio):**
- Implementation: `backend/app/api/portfolio.py` — create `APIRouter`, define route handlers
- Tests: `backend/tests/api/test_portfolio.py`
- Register in: `backend/app/main.py` via `app.include_router(portfolio_router)`

**New database query:**
- Implementation: `backend/app/db/queries.py`
- Tests: `backend/tests/db/test_queries.py`

**New market data provider:**
- Implementation: `backend/app/market/my_provider.py` — implement `MarketDataSource`
- Register in: `backend/app/market/factory.py` — add branch to `create_market_data_source()`
- Tests: `backend/tests/market/test_my_provider.py`

**Frontend components (when frontend/ is created):**
- Follow Next.js App Router conventions under `frontend/src/`
- Component files: PascalCase — `WatchlistPanel.tsx`, `TradeBar.tsx`
- Hooks: `use` prefix — `useSSE.ts`, `usePortfolio.ts`

**New utility/shared code:**
- Backend shared helpers: create a dedicated module in `backend/app/` (e.g., `backend/app/utils.py`)
- Do not put utilities inside `market/` — that module has a narrow scope

## Special Directories

**`backend/.venv/`:**
- Purpose: Python virtual environment managed by uv
- Generated: Yes
- Committed: No (gitignored via `.venv`)

**`backend/.pytest_cache/`:**
- Purpose: pytest result cache
- Generated: Yes
- Committed: No (gitignored)

**`.planning/codebase/`:**
- Purpose: GSD agent-generated codebase analysis documents
- Generated: Yes (by map-codebase agent)
- Committed: Yes

---

*Structure analysis: 2026-03-16*
