# Pitfalls Research

**Domain:** AI Trading Workstation (FastAPI + Next.js static export + SQLite + SSE + LLM)
**Researched:** 2026-03-16
**Confidence:** HIGH (most pitfalls verified via official docs and multiple sources)

## Critical Pitfalls

### Pitfall 1: SQLite Concurrent Write Contention ("database is locked")

**What goes wrong:**
FastAPI handles requests concurrently via async. When a trade executes, a portfolio snapshot records, and a chat message saves in overlapping requests, all three attempt SQLite writes simultaneously. SQLite allows only one writer at a time. Without WAL mode and a busy timeout, the second and third writers get immediate "database is locked" errors and the request fails.

**Why it happens:**
Developers test with single requests and never hit write contention. SQLite's default journal mode (DELETE) blocks readers during writes too, making things worse. The default busy timeout is 0ms -- meaning immediate failure rather than retry.

**How to avoid:**
Configure SQLite pragmas at connection creation time:
```sql
PRAGMA journal_mode = WAL;
PRAGMA busy_timeout = 5000;
PRAGMA synchronous = NORMAL;
PRAGMA foreign_keys = ON;
```
Use a single database connection (or a serialized connection pool) for all writes. Since this is single-user, a single `aiosqlite` connection with WAL mode is sufficient. Keep write transactions short -- insert and commit, do not hold transactions open across async awaits.

**Warning signs:**
- Intermittent 500 errors on trade execution when the portfolio snapshot background task is running
- "database is locked" in server logs
- Errors only appear under concurrent operations, never in isolated unit tests

**Phase to address:**
Database layer phase (first backend phase). Set pragmas in the database initialization code before any other module touches the database.

---

### Pitfall 2: Trade Execution Race Conditions (Double-Spend on Cash Balance)

**What goes wrong:**
Two near-simultaneous buy requests both read the same cash balance ($10,000), both validate they have enough cash, and both execute. The user ends up spending more than they have. Similarly, two sells of the same position can oversell shares. The LLM chat endpoint can trigger trades concurrently with manual trade bar submissions.

**Why it happens:**
The read-validate-write sequence is not atomic. FastAPI processes requests concurrently, and without explicit serialization, the classic TOCTOU (time-of-check-to-time-of-use) bug appears. This is especially subtle because the LLM auto-execution path and the manual trade path both call the same trade logic but from different request handlers.

**How to avoid:**
Wrap the entire trade execution (read balance, validate, update position, update cash, insert trade record) in a single SQLite transaction with `BEGIN IMMEDIATE`. SQLite's `BEGIN IMMEDIATE` acquires a write lock at transaction start rather than on first write, preventing the interleaved read problem. Since SQLite serializes writes, this effectively serializes trade execution. Alternatively, use an asyncio Lock around the trade function.

**Warning signs:**
- Cash balance going negative in the database
- Position quantities not matching trade history sums
- Unit tests pass but integration tests with concurrent requests fail

**Phase to address:**
Portfolio/trading API phase. The trade endpoint must be built with transactional integrity from day one -- this cannot be retrofitted without risk.

---

### Pitfall 3: LLM Structured Output Returns Invalid or Unexpected Schema

**What goes wrong:**
LiteLLM with Gemini structured outputs returns JSON that is syntactically valid but does not match the expected schema. For example: the `trades` array contains objects with `"amount"` instead of `"quantity"`, or the `side` field contains `"purchase"` instead of `"buy"`. The auto-execution code blindly trusts the schema and either crashes with a KeyError or executes an unintended trade.

**Why it happens:**
Structured output with Gemini models (especially via LiteLLM) has known issues. LiteLLM issue trackers show that structured output "doesn't work correctly" with some Gemini models -- output is "almost correct" but not valid. The `gemini-3.1-flash-lite-preview` model specified in the plan is a preview model, making schema adherence even less reliable. Additionally, if the LLM reaches its token limit mid-generation, the JSON may be truncated.

**How to avoid:**
1. Validate LLM responses with Pydantic models before processing. Define `ChatResponse`, `TradeAction`, and `WatchlistAction` as strict Pydantic models with field validators.
2. Enable LiteLLM's client-side JSON schema validation: `litellm.enable_json_schema_validation = True`.
3. Wrap all auto-execution in try/except -- if parsing fails, return the raw message text to the user with a note that the action could not be completed.
4. Never execute a trade from LLM output without the same validation that manual trades go through (sufficient cash, valid ticker, positive quantity).

**Warning signs:**
- Occasional chat responses that show raw JSON or error traces instead of natural language
- Trade execution errors that only happen via chat, never via the trade bar
- KeyError or ValidationError in logs from the chat endpoint

**Phase to address:**
LLM integration phase. Build Pydantic validation models before implementing auto-execution. Test with adversarial prompts that try to produce edge-case outputs.

---

### Pitfall 4: Lightweight Charts is Client-Side Only -- Breaks with Next.js SSR/Import

**What goes wrong:**
Importing `lightweight-charts` in a Next.js component causes a build error or runtime crash: `ReferenceError: window is not defined`. The library requires DOM/canvas APIs that do not exist during server-side rendering or static export pre-rendering.

**Why it happens:**
Next.js pre-renders pages even with `output: 'export'`. During the build step, component code runs in a Node.js environment where `window`, `document`, and `HTMLCanvasElement` do not exist. Lightweight Charts accesses these globals at import time, not just at render time.

**How to avoid:**
Use dynamic imports with SSR disabled:
```typescript
import dynamic from 'next/dynamic';
const Chart = dynamic(() => import('../components/Chart'), { ssr: false });
```
Alternatively, guard the import with a `typeof window !== 'undefined'` check and lazy-load the library inside a `useEffect`. The chart component itself must only be rendered client-side.

**Warning signs:**
- `next build` fails with "window is not defined" or "document is not defined"
- Charts render in dev mode (`next dev`) but break in production build
- Blank chart areas after static export

**Phase to address:**
Frontend phase. Establish the `dynamic import with ssr: false` pattern when creating the first chart component. Apply consistently to all charting components.

---

### Pitfall 5: SSE Connection Limit (6 per Domain) Blocks Other Requests

**What goes wrong:**
When using HTTP/1.1, browsers enforce a maximum of 6 concurrent connections per domain. An SSE connection is long-lived and occupies one of these slots permanently. If the app opens multiple SSE connections (e.g., one for prices and one for portfolio updates, or the user opens multiple tabs), the browser runs out of connection slots. New API requests (trades, chat) queue and appear to hang.

**Why it happens:**
EventSource opens a persistent HTTP connection. Unlike WebSockets, SSE connections count against the normal HTTP connection pool. Developers test with a single tab and never encounter the limit. The problem surfaces when users open 2-3 tabs or when the frontend inadvertently creates multiple EventSource instances (e.g., due to React re-renders without cleanup).

**How to avoid:**
1. Use exactly one SSE connection for all streaming data (prices). The current design already does this correctly.
2. Clean up EventSource on component unmount -- use `useEffect` cleanup to call `eventSource.close()`.
3. Consider a singleton pattern for the EventSource at the app level, not per-component.
4. Add HTTP/2 support in the Docker container (via uvicorn with `--h2` flag or a reverse proxy), which removes the 6-connection limit entirely.

**Warning signs:**
- App works in one tab but hangs when opened in a second tab
- API calls (trade, chat) intermittently time out
- Network tab shows requests stuck in "pending" state

**Phase to address:**
Frontend phase. Implement EventSource as a singleton service/context provider, not inside individual components. Ensure cleanup on unmount.

---

### Pitfall 6: Next.js Static Export Unsupported Features Silently Break

**What goes wrong:**
Developers use Next.js features that require a server -- `next/image` optimization, API routes, middleware, `getServerSideProps`, `headers()`, `cookies()` -- and the static export either silently drops them or fails at build time with cryptic errors. The app works perfectly in `next dev` but the production build is broken or missing functionality.

**How to avoid:**
1. Set `output: 'export'` in `next.config.js` from the very first commit. Never develop without it.
2. Use `<img>` tags or configure `images: { unoptimized: true }` in next.config.js instead of `next/image` optimization.
3. No API routes in `pages/api/` or `app/api/` -- all API calls go to the FastAPI backend.
4. No `getServerSideProps`, no middleware, no `headers()`/`cookies()`.
5. Run `next build` frequently during development to catch incompatible features early.

**Warning signs:**
- Features work in `next dev` but disappear or error after `next build`
- Build warnings about unsupported features with `output: 'export'`
- `out/` directory missing expected pages

**Phase to address:**
Frontend scaffolding (start of frontend phase). Configure `output: 'export'` and `images: { unoptimized: true }` immediately. Run a build before adding any features.

---

### Pitfall 7: Portfolio Snapshot Background Task Outlives Request Context

**What goes wrong:**
The background task that records portfolio snapshots every 30 seconds needs access to both the price cache (for current prices) and the database (for positions and cash). If it uses a database connection tied to a request lifecycle, the connection is closed. If it creates its own connection without WAL mode, it conflicts with request-driven writes. If the task crashes silently, the P&L chart has no data and the frontend shows an empty chart with no error.

**Why it happens:**
FastAPI background tasks and lifespan-managed tasks have different lifecycles than request handlers. Developers wire up the snapshot task to use request-scoped dependencies and it works in testing (where requests are active) but fails in production when the task runs between requests.

**How to avoid:**
Use FastAPI's lifespan context manager to start/stop the background task. Give it its own database connection (or use the same shared connection with WAL mode). Log every snapshot write. Add error handling that logs failures but does not crash the task -- use `try/except` inside the loop with exponential backoff on repeated failures.

**Warning signs:**
- P&L chart shows no data points or stops updating after a while
- "connection closed" errors in logs from the snapshot task
- Task works for a few minutes then silently stops

**Phase to address:**
Portfolio/trading API phase. Design the background task alongside the database layer, not as an afterthought.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Raw SQL instead of ORM | Simpler, no SQLAlchemy dependency | Harder to maintain, SQL injection risk if not parameterized | Acceptable for this demo if all queries use parameterized statements |
| Single DB connection (no pool) | Zero config, no pool management | Cannot scale to concurrent users | Acceptable -- single-user demo by design |
| No database migrations | Lazy init is simple | Schema changes require DB deletion | Acceptable -- demo app, schema is small and stable |
| Storing chat history in SQLite | Simple, no external service | Chat history grows unbounded | Acceptable -- demo lifespan is short |
| No retry logic on LLM calls | Less code, faster response | Single LLM timeout kills the chat feature | Add basic retry (1 retry with 5s timeout) -- low effort, high value |

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| LiteLLM + Gemini | Passing `response_format` with `tools` simultaneously -- causes broken output | Use structured output OR tools, not both. For this project, use `response_format` only (no function calling) |
| LiteLLM + Gemini | Assuming `gemini-3.1-flash-lite-preview` is stable | Preview models change behavior between versions. Pin the model string, add a fallback model, and validate all outputs |
| EventSource + FastAPI | Not sending SSE heartbeat comments, causing proxy/CDN timeouts | Send `:heartbeat\n\n` comment every 15 seconds even when no data changes |
| Next.js static export + FastAPI | Using `next/image` with default loader | Set `images: { unoptimized: true }` in next.config.js |
| SQLite + Docker volume | Mounting a directory but writing DB to wrong path | Ensure backend writes to the mounted path (`/app/db/finally.db`), not a relative path |
| aiosqlite | Opening connection per request (connection pooling mindset from Postgres) | Open one connection at startup, reuse for all requests. SQLite does not benefit from connection pools |

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Re-rendering entire watchlist on every SSE tick | UI stutters at 500ms update interval with 10+ tickers | Use React.memo on ticker rows, update only changed tickers via key-based reconciliation | Noticeable with 15+ tickers on mid-range hardware |
| Accumulating sparkline data without limit | Memory grows linearly, page slows after hours | Cap sparkline arrays at ~500 points, drop oldest on new push | After ~4 hours of continuous streaming |
| Portfolio heatmap recalculating on every price tick | Treemap layout thrashes, visual jitter | Throttle heatmap updates to every 2-5 seconds, not every tick | Immediate -- treemap layout is expensive |
| Querying all trades for P&L on every portfolio request | Response time grows with trade count | Cache position state in `positions` table (already in schema). Only query trades for history view | After 100+ trades |
| SSE endpoint holding GIL during JSON serialization | Other async tasks delayed | Pre-serialize price data, keep SSE yield minimal | Unlikely at demo scale, but good practice |

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| No ticker validation on watchlist add | Arbitrary strings sent to Massive API or stored in DB; potential injection if raw SQL used | Validate ticker format: 1-5 uppercase alpha characters, reject everything else |
| LLM prompt injection via chat | User crafts message that makes LLM ignore system prompt and execute unintended trades | Validate all LLM-proposed trades through the same business logic as manual trades. The LLM cannot bypass validation. |
| Exposing full error tracebacks in API responses | Internal paths, library versions leaked | Use FastAPI exception handlers to return clean error messages in production |
| SQLite file accessible if volume misconfigured | Database file readable by other containers on shared Docker host | Use named volumes (not bind mounts to host directories) for production-like deployments |

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| No loading state during LLM response | User thinks chat is broken, sends duplicate messages | Show typing indicator immediately on send, disable input until response |
| Price flash animation too aggressive | Entire watchlist flashing red/green every 500ms is visually overwhelming | Flash only the price cell, use subtle background color (10-15% opacity), fade over 500ms |
| No feedback on failed trades | User clicks buy, nothing happens, cash unchanged | Show inline error message in trade bar area: "Insufficient cash: need $X, have $Y" |
| Heatmap unreadable with 1-2 positions | Single rectangle fills entire area, no visual information | Show minimum 4 cells (pad with cash position), or switch to a simple bar chart when positions < 3 |
| Chat actions not visually distinct from messages | User cannot tell which trades the AI executed | Render trade confirmations as distinct card/badge components with ticker, side, quantity, price |
| SSE disconnect shows no indication | Prices freeze, user thinks market is flat | Show connection status dot in header (green/yellow/red per plan). Re-establish connection automatically. |

## "Looks Done But Isn't" Checklist

- [ ] **Trade execution:** Often missing atomic transactions -- verify cash and position updates happen in one transaction, not separate queries
- [ ] **Portfolio value calculation:** Often uses stale prices -- verify it reads from price cache, not database, for current prices
- [ ] **SSE reconnection:** Often reconnects but loses state -- verify sparkline data persists across reconnections (it is client-side accumulated, so EventSource reconnect is fine, but the component must not reset state)
- [ ] **LLM mock mode:** Often returns static strings -- verify mock responses include `trades` and `watchlist_changes` arrays so the auto-execution path is tested
- [ ] **Docker volume persistence:** Often works in dev but not production -- verify stopping and restarting the container preserves trades and portfolio state
- [ ] **Static export routing:** Often works with `next dev` router -- verify that refreshing the page in the browser after static export does not 404 (single-page app needs fallback routing in FastAPI)
- [ ] **Chat history context:** Often sends all messages to LLM -- verify only last 10 messages are sent (per plan) to stay within token limits
- [ ] **Position closure:** Often updates quantity but leaves stale row -- verify selling all shares removes the position row and returns `position: null` in the response

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| SQLite "database is locked" in production | LOW | Add WAL mode and busy_timeout pragmas. No schema change needed. |
| Trade race condition (negative cash) | MEDIUM | Add transaction locking, audit all trades against history, reconcile cash balance |
| LLM returns invalid structured output | LOW | Add Pydantic validation layer. Existing code continues to work, validation wraps it |
| Lightweight Charts SSR crash | LOW | Wrap in dynamic import. Isolated fix, no architectural change |
| SSE connection exhaustion | LOW | Refactor EventSource to singleton. Localized frontend change |
| Next.js static export feature incompatibility | HIGH if discovered late | Must rewrite affected components. Prevention (configure early) is critical |
| Background task silently dies | MEDIUM | Add health check endpoint that reports last snapshot time. Add logging. |

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| SQLite write contention | Database layer | Run concurrent write test: 10 simultaneous inserts succeed |
| Trade race conditions | Portfolio/trading API | Integration test: two concurrent buys with insufficient total cash -- only one succeeds |
| LLM structured output failures | LLM integration | Unit test: feed malformed JSON, partial JSON, wrong-schema JSON -- all handled gracefully |
| Lightweight Charts SSR crash | Frontend scaffolding | `next build` succeeds with chart component present |
| SSE connection limit | Frontend SSE integration | Open app in 3 tabs simultaneously, all function correctly |
| Static export incompatibility | Frontend scaffolding (day 1) | `next build && next export` produces working `out/` directory before any features added |
| Background task lifecycle | Portfolio/trading API | Restart container, verify snapshots resume within 30 seconds |
| Portfolio value with stale prices | Portfolio/trading API | Compare `/api/portfolio` total_value against manual calculation from price cache |

## Sources

- [SQLite WAL mode documentation](https://sqlite.org/wal.html)
- [SQLite concurrent writes and "database is locked" errors](https://tenthousandmeters.com/blog/sqlite-concurrent-writes-and-database-is-locked-errors/)
- [Next.js Static Exports guide](https://nextjs.org/docs/pages/guides/static-exports)
- [Next.js API Routes in Static Export warning](https://nextjs.org/docs/messages/api-routes-static-export)
- [MDN: Using server-sent events](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events)
- [FastAPI SSE tutorial](https://fastapi.tiangolo.com/tutorial/server-sent-events/)
- [LiteLLM Structured Outputs (JSON Mode) docs](https://docs.litellm.ai/docs/completion/json_mode)
- [LiteLLM + Gemini structured output issues (GitHub #1575)](https://github.com/openai/openai-agents-python/issues/1575)
- [LiteLLM doesn't support structured output correctly (GitHub #1967)](https://github.com/google/adk-python/issues/1967)
- [Lightweight Charts documentation](https://tradingview.github.io/lightweight-charts/docs)
- [Lightweight Charts real-time updates tutorial](https://tradingview.github.io/lightweight-charts/tutorials/demos/realtime-updates)
- [Output Constraints as Attack Surface (arXiv)](https://arxiv.org/html/2503.24191v1)
- [Understanding Race Conditions in Automated Trading](https://blog.traderspost.io/article/understanding-race-conditions-in-automated-trading)
- [FastAPI async database connections](https://oneuptime.com/blog/post/2026-02-02-fastapi-async-database/view)
- [SQLAlchemy Database Locks Using FastAPI](https://medium.com/@mojimich2015/sqlalchemy-database-locks-using-fastapi-a-simple-guide-3e7dcd552d87)

---
*Pitfalls research for: FinAlly AI Trading Workstation*
*Researched: 2026-03-16*
