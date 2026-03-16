# Codebase Concerns

**Analysis Date:** 2026-03-16

## Tech Debt

**API, DB, and LLM source files do not exist — only compiled .pyc artifacts:**
- Issue: `backend/app/api/`, `backend/app/db/`, and `backend/app/llm/` directories contain only `__pycache__` subdirectories. Source `.py` files for routers, database logic, LLM client, and prompts have not been created yet. The `.pyc` files present appear to be residual artifacts from a previous work session.
- Files: `backend/app/api/` (no `.py` files), `backend/app/db/` (no `.py` files), `backend/app/llm/` (no `.py` files)
- Impact: The FastAPI application entry point (`backend/app/main.py`) also does not exist. The app cannot run. Only the market data subsystem is functional.
- Fix approach: Implement all missing modules per PLAN.md contracts. Build order: DB layer → API routes → LLM module → main.py entry point.

**LiteLLM missing from dependencies:**
- Issue: `PLAN.md` specifies `litellm` as the LLM client library, but `backend/pyproject.toml` does not list it as a dependency, and `backend/uv.lock` has zero occurrences of `litellm`. When the LLM module is implemented, it will fail to import at runtime.
- Files: `backend/pyproject.toml`
- Impact: `POST /api/chat` will fail on first import unless `litellm` is added.
- Fix approach: `uv add litellm` in `backend/` before implementing `backend/app/llm/chat.py`.

**`db/` volume mount directory missing from repository:**
- Issue: `PLAN.md` specifies a top-level `db/` directory with a `.gitkeep` so Docker can volume-mount it. Neither the directory nor the `.gitkeep` exist in the repo.
- Files: `db/` (does not exist)
- Impact: Docker `run -v finally-data:/app/db` will fail or create an anonymous volume on an empty path. Database writes will not persist across container restarts.
- Fix approach: Create `db/.gitkeep` and ensure `.gitignore` ignores `db/finally.db`.

**`finally.db` not in `.gitignore`:**
- Issue: `.gitignore` ignores `db.sqlite3` and `db.sqlite3-journal` (Django-style names) but has no pattern for `db/finally.db` or `*.db`. If the runtime database file is created during local development before Docker setup, it will appear as untracked and could be accidentally committed.
- Files: `.gitignore`
- Impact: Low probability but could commit a database containing fake trade data or (in future) user config.
- Fix approach: Add `db/finally.db` to `.gitignore`.

**`.env.example` missing:**
- Issue: `README.md` instructs users to `cp .env.example .env` as the first setup step. No `.env.example` file exists in the repository.
- Files: `.env.example` (does not exist)
- Impact: New users following the README will hit an immediate error. The actual `.env` file is gitignored (correct) but without an example, required variables are undocumented at the file level.
- Fix approach: Create `.env.example` with `GOOGLE_API_KEY=`, `MASSIVE_API_KEY=`, `LLM_MOCK=false` as placeholders.

**Frontend directory is empty:**
- Issue: `frontend/` directory exists but contains no files — no `package.json`, no Next.js setup, no source code.
- Files: `frontend/` (empty)
- Impact: The Docker multi-stage build (Stage 1 runs `npm install && npm run build`) will fail. The app cannot be containerized.
- Fix approach: Initialize Next.js project in `frontend/` with TypeScript, Tailwind CSS, and `output: 'export'` configuration.

**No Dockerfile or docker-compose files exist:**
- Issue: `README.md` and `PLAN.md` specify a multi-stage Dockerfile and `test/docker-compose.test.yml`. Neither exists.
- Files: `Dockerfile` (does not exist), `test/docker-compose.test.yml` (does not exist), `scripts/` (does not exist)
- Impact: The app cannot be built or run via Docker. Start/stop scripts are missing. E2E tests have no infrastructure.
- Fix approach: Implement Dockerfile per PLAN.md §11 spec; add `test/docker-compose.test.yml`; add `scripts/start_mac.sh`, `scripts/stop_mac.sh`, `scripts/start_windows.ps1`, `scripts/stop_windows.ps1`.

## Known Bugs

**`PriceCache.version` property reads `_version` without the lock:**
- Symptoms: SSE stream at `stream.py:76` reads `price_cache.version` outside any lock. The `_version` int is incremented under `self._lock` in `update()`, but the `version` property at line 66-67 accesses `self._version` directly with no lock.
- Files: `backend/app/market/cache.py` (lines 64-67)
- Trigger: In CPython, integer reads are effectively atomic due to the GIL, making this safe in practice. However it is technically incorrect for a "thread-safe" class and would be a real bug on non-CPython runtimes (Jython, PyPy with parallel GC, etc.).
- Workaround: CPython GIL masks the bug currently.

## Security Considerations

**No input validation on ticker symbols:**
- Risk: `add_ticker` in both `SimulatorDataSource` and `MassiveDataSource` normalizes case (`.upper().strip()`) but performs no validation of ticker format. Arbitrary strings are added to the simulator and passed directly to the Massive REST API.
- Files: `backend/app/market/simulator.py` (line 242-250), `backend/app/market/massive_client.py` (lines 66-70)
- Current mitigation: Massive API will reject invalid tickers; simulator seeds them with random prices.
- Recommendations: When `/api/watchlist` POST is implemented, validate ticker format (1-5 uppercase letters) before calling `add_ticker`.

**No authentication or authorization:**
- Risk: All API endpoints will be unauthenticated. Any process that can reach port 8000 can read portfolio state, execute trades, and send chat messages.
- Files: All future `backend/app/api/` routes
- Current mitigation: Single-user design, Docker-only deployment, local network by default.
- Recommendations: Acceptable for the demo scope. Add a warning in README if deploying publicly.

**`.env` file committed without `.env.example`:**
- Risk: The `.env` file is correctly gitignored. However, `.env.example` is missing, which increases the chance a developer copies `.env` and exposes their `GOOGLE_API_KEY`.
- Files: `.gitignore`, `.env.example` (missing)
- Current mitigation: `.gitignore` blocks `.env`.
- Recommendations: Create `.env.example` immediately to establish the safe pattern.

## Performance Bottlenecks

**GBM simulator calls `_rebuild_cholesky()` synchronously on ticker add/remove:**
- Problem: `GBMSimulator._rebuild_cholesky()` runs in the asyncio event loop (called from `SimulatorDataSource.add_ticker/remove_ticker`, which are `async def` but contain no `await`). For small n (< 20 tickers) this is negligible. For a heavily extended watchlist it could briefly block the event loop.
- Files: `backend/app/market/simulator.py` (lines 120-134, 154-172)
- Cause: NumPy `np.linalg.cholesky()` is synchronous and called directly in the async path.
- Improvement path: Wrap `_rebuild_cholesky()` in `asyncio.to_thread()` if watchlist exceeds ~30 tickers, or accept the constraint given demo scope.

**SSE stream sends all prices every interval even when nothing changed:**
- Problem: The version-check optimization in `stream.py` (lines 76-84) correctly skips the yield when `current_version == last_version`. However, version increments on every simulator tick (every 500ms), so the SSE always fires at 500ms cadence and always includes all tracked tickers in a single payload.
- Files: `backend/app/market/stream.py` (lines 75-84)
- Cause: Design decision — simple batch push rather than per-ticker delta events.
- Improvement path: Acceptable for demo. For scale, send only changed tickers per tick.

## Fragile Areas

**`MassiveDataSource._tickers` list is mutated from event loop while `_fetch_snapshots` reads it in a thread:**
- Files: `backend/app/market/massive_client.py` (lines 68-69, 74, 97, 127)
- Why fragile: `add_ticker` and `remove_ticker` mutate `self._tickers` from the asyncio event loop. `_fetch_snapshots` runs via `asyncio.to_thread()` and passes `self._tickers` directly to the REST API call (line 127). If a ticker is added or removed while the thread is reading `self._tickers`, the list could be in a partially-mutated state. Python list mutations are not thread-safe despite the GIL for non-atomic operations.
- Safe modification: Pass a copy — change line 127 from `tickers=self._tickers` to `tickers=list(self._tickers)`. The `_poll_once` function should snapshot the list before calling `to_thread`.
- Test coverage: No existing test exercises concurrent `add_ticker` / `_poll_once` races.

**GBMSimulator internal state has no locking:**
- Files: `backend/app/market/simulator.py` (GBMSimulator class, no Lock anywhere)
- Why fragile: `GBMSimulator.step()` iterates and mutates `self._tickers` and `self._prices`. `add_ticker` and `remove_ticker` are called from `SimulatorDataSource.add_ticker/remove_ticker` (async methods). Since all of this runs on the same asyncio event loop (no `to_thread`), concurrent access is serialized by the event loop and is safe today. If any caller ever moves these methods off the event loop, races would occur silently.
- Safe modification: Keep all GBMSimulator access on the event loop; never call it from a thread.

**`stream.py` SSE endpoint has no test coverage of the HTTP path:**
- Files: `backend/app/market/stream.py` (lines 25-49, 63-88 — 31% coverage)
- Why fragile: The `stream_prices` endpoint and `_generate_events` generator are untested. If a regression is introduced in the SSE format or disconnect handling, no test will catch it.
- Test coverage: Only the router factory function is implicitly covered via import. The streaming path requires an async HTTP test client (e.g., `httpx.AsyncClient` with FastAPI `TestClient`).
- Priority: Medium — market data subsystem is otherwise well tested.

## Scaling Limits

**SQLite single-file database:**
- Current capacity: Single writer, single file, no connection pooling. Suitable for demo/development.
- Limit: Concurrent write operations (trade + portfolio snapshot + chat message in the same request) will serialize on the SQLite write lock. Acceptable for single-user demo; breaks under concurrent users.
- Scaling path: Not applicable for demo scope. Future multi-user would require Postgres.

**In-memory `PriceCache` is not persisted:**
- Current capacity: Unlimited tickers, sub-millisecond reads.
- Limit: All price history is lost on process restart. Sparklines and per-session price history cannot be recovered.
- Scaling path: Acceptable by design — SSE clients rebuild their own sparklines from the stream.

## Dependencies at Risk

**`massive` package is a thin Polygon.io wrapper of uncertain provenance:**
- Risk: The `massive>=1.0.0` dependency (`backend/pyproject.toml`) is not a well-known package. Its API surface (e.g., `SnapshotMarketType`, `RESTClient.get_snapshot_all`) is used directly in `massive_client.py`. If the package is unmaintained or its API changes, real market data is broken.
- Impact: `MassiveDataSource` fails at startup or at poll time. Simulator fallback still works.
- Migration plan: The `MarketDataSource` interface makes it straightforward to swap to a different Polygon.io client or direct `httpx` calls.

**`litellm` not yet declared as a dependency:**
- Risk: See Tech Debt section above. When the LLM module is built, `litellm` must be added to `pyproject.toml` before implementation.
- Impact: Import error at startup when `app/llm/chat.py` is imported by the API router.
- Migration plan: `uv add litellm` before implementing LLM module.

## Missing Critical Features

**No FastAPI application entry point:**
- Problem: `backend/app/main.py` does not exist. Without it, `uvicorn app.main:app` (the Docker CMD) fails.
- Blocks: Everything — the app cannot start. Docker container will exit immediately.

**No database layer:**
- Problem: `backend/app/db/` has no source files. Portfolio state, trades, watchlist, and chat history cannot be persisted.
- Blocks: All API routes (`/api/portfolio`, `/api/watchlist`, `/api/chat`); LLM context loading; portfolio snapshots.

**No REST API routes:**
- Problem: `backend/app/api/` has no source files. Only the SSE streaming endpoint (`/api/stream/prices`) exists via `backend/app/market/stream.py`.
- Blocks: All user-facing functionality except price streaming.

**No E2E test infrastructure:**
- Problem: `test/` directory contains only `node_modules` with Playwright packages. No test files, no `playwright.config.ts`, no `docker-compose.test.yml`.
- Blocks: E2E test execution; CI validation of the full stack.

## Test Coverage Gaps

**SSE streaming endpoint is untested as an HTTP endpoint:**
- What's not tested: `_generate_events` async generator (connection, price emission, disconnect detection, retry header)
- Files: `backend/app/market/stream.py` (lines 25-49, 63-88)
- Risk: Breaking changes to SSE format or disconnect handling go undetected.
- Priority: Medium

**API, DB, and LLM modules have zero tests (because they don't exist yet):**
- What's not tested: Trade execution logic, P&L calculations, portfolio endpoint response shapes, watchlist CRUD, chat message flow, LLM structured output parsing, mock mode.
- Files: All of `backend/app/api/`, `backend/app/db/`, `backend/app/llm/`
- Risk: High — these are the core business logic paths. Must be built with tests from the start.
- Priority: High

**Frontend has no tests:**
- What's not tested: All React components, price flash animation, SSE connection handling, trade form, portfolio calculations.
- Files: `frontend/` (empty)
- Risk: High — entire UI layer is untested.
- Priority: High (implement alongside frontend build)

---

*Concerns audit: 2026-03-16*
