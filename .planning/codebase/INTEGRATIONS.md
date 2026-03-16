# External Integrations

**Analysis Date:** 2026-03-16

## APIs & External Services

**Market Data (optional):**
- Massive (Polygon.io) — real-time US stock price snapshots
  - SDK/Client: `massive` 2.2.0 Python package; `RESTClient` class
  - Auth: `MASSIVE_API_KEY` environment variable
  - Endpoint: `GET /v2/snapshot/locale/us/markets/stocks/tickers` (all tickers in one call)
  - Rate limit: Free tier 5 req/min → 15s poll interval; paid tiers 2-5s
  - Implementation: `backend/app/market/massive_client.py` — `MassiveDataSource`
  - Activation: set and non-empty `MASSIVE_API_KEY`; falls back to simulator if absent

**AI / LLM (planned — not yet implemented):**
- Google Gemini via LiteLLM — structured output chat assistant
  - SDK/Client: `litellm` (not yet added to `pyproject.toml`)
  - Model: `gemini/gemini-3.1-flash-lite-preview`
  - Auth: `GOOGLE_API_KEY` environment variable
  - Pattern: structured JSON output with `message`, `trades`, `watchlist_changes` fields
  - Mock mode: `LLM_MOCK=true` returns deterministic responses (for testing)

## Data Storage

**Databases:**
- SQLite — single-file embedded database
  - File path: `db/finally.db` (volume-mounted at `/app/db/finally.db` in Docker)
  - Connection: no env var; hardcoded path, resolved relative to container working directory
  - Client: Python stdlib `sqlite3` or `aiosqlite` (not yet implemented)
  - Initialization: lazy — backend creates schema and seeds data on first startup if file missing
  - Schema: 6 tables: `users_profile`, `watchlist`, `positions`, `trades`, `portfolio_snapshots`, `chat_messages`
  - All tables include `user_id TEXT DEFAULT "default"` for future multi-user support

**File Storage:**
- Local filesystem only — SQLite file on Docker volume `finally-data`

**Caching:**
- In-memory `PriceCache` — thread-safe store in `backend/app/market/cache.py`
  - Holds latest price, previous price, and timestamp per ticker
  - Monotonic version counter for SSE change detection
  - Not persisted; rebuilt on each startup from market data source

## Authentication & Identity

**Auth Provider:**
- None — single-user application, no login or signup
- All database rows use hardcoded `user_id = "default"`

## Monitoring & Observability

**Error Tracking:**
- None

**Logs:**
- Python stdlib `logging` throughout backend
- `rich` library used in `backend/market_data_demo.py` for development terminal dashboard
- Log levels: DEBUG for poll cycle details, INFO for lifecycle events, ERROR for poll failures

## CI/CD & Deployment

**Hosting:**
- Docker container, port 8000
- Designed for single-command local launch: `docker run -v finally-data:/app/db -p 8000:8000 --env-file .env finally`
- Optional cloud targets: AWS App Runner, Render, any container platform

**CI Pipeline:**
- GitHub Actions — two workflows in `.github/workflows/`:
  - `claude.yml` — Claude Code integration
  - `claude-code-review.yml` — automated code review

## Environment Configuration

**Required env vars:**
- `GOOGLE_API_KEY` — Google API key for Gemini LLM (required for chat functionality)

**Optional env vars:**
- `MASSIVE_API_KEY` — Polygon.io key for real market data; omit to use GBM simulator
- `LLM_MOCK` — set `true` for deterministic mock LLM in tests; default `false`

**Secrets location:**
- `.env` file at project root (gitignored)
- Mounted into Docker container via `--env-file .env`
- `.env.example` planned but not yet present in repo

## Webhooks & Callbacks

**Incoming:**
- None

**Outgoing:**
- None

## Real-Time Streaming

**SSE (Server-Sent Events):**
- Endpoint: `GET /api/stream/prices`
- Implementation: `backend/app/market/stream.py` — `create_stream_router(price_cache)`
- Push cadence: ~500ms (checks `PriceCache.version` for changes)
- Client reconnect: `retry: 1000` directive; browser `EventSource` handles automatically
- Payload: JSON map of all tracked tickers to their `PriceUpdate.to_dict()` snapshots
- Nginx buffering disabled via `X-Accel-Buffering: no` header

---

*Integration audit: 2026-03-16*
