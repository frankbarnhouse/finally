# Requirements: FinAlly — AI Trading Workstation

**Defined:** 2026-03-16
**Core Value:** Users can interact with a live-updating trading terminal where an AI assistant can analyze their portfolio and execute trades through natural language

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Database

- [x] **DB-01**: SQLite database auto-creates schema and seeds default data on first request (lazy init)
- [x] **DB-02**: Default user profile created with $10,000 cash balance
- [x] **DB-03**: Default watchlist seeded with 10 tickers (AAPL, GOOGL, MSFT, AMZN, TSLA, NVDA, META, JPM, V, NFLX)
- [x] **DB-04**: WAL mode and busy_timeout configured at database initialization

### Watchlist

- [x] **WATCH-01**: User can view watchlist tickers with latest prices
- [x] **WATCH-02**: User can add a ticker to the watchlist
- [x] **WATCH-03**: User can remove a ticker from the watchlist

### Portfolio

- [x] **PORT-01**: User can view all positions with cash balance and total portfolio value
- [x] **PORT-02**: User can execute buy market orders filled at current price
- [x] **PORT-03**: User can execute sell market orders filled at current price
- [x] **PORT-04**: Trade validation rejects insufficient cash (buy) or insufficient shares (sell)
- [x] **PORT-05**: Selling entire position removes the position row (position returns null)
- [ ] **PORT-06**: Portfolio snapshots recorded every 30 seconds and immediately after each trade
- [ ] **PORT-07**: User can retrieve portfolio value history for P&L chart

### LLM Chat

- [ ] **CHAT-01**: User can send messages and receive AI responses with full portfolio context
- [ ] **CHAT-02**: AI can auto-execute trades via structured JSON output
- [ ] **CHAT-03**: AI can add/remove watchlist tickers via structured JSON output
- [ ] **CHAT-04**: Last 10 conversation messages included in LLM context
- [ ] **CHAT-05**: LLM mock mode returns deterministic responses when LLM_MOCK=true
- [ ] **CHAT-06**: Failed trade/watchlist actions appended to response message text

### Frontend

- [ ] **UI-01**: Dark trading terminal layout with Bloomberg-inspired aesthetic (backgrounds ~#0d1117)
- [ ] **UI-02**: Watchlist panel with live-updating prices from SSE stream
- [ ] **UI-03**: Price flash animations (green uptick, red downtick) fading over ~500ms
- [ ] **UI-04**: Sparkline mini-charts in watchlist accumulated from SSE since page load
- [ ] **UI-05**: Main chart area showing selected ticker price history (click ticker to select)
- [ ] **UI-06**: Portfolio heatmap (treemap) sized by position weight, colored by P&L
- [ ] **UI-07**: P&L line chart showing portfolio value over time from snapshots
- [ ] **UI-08**: Positions table: ticker, quantity, avg cost, current price, unrealized P&L, % change
- [ ] **UI-09**: Trade bar with ticker input, quantity input, buy button, sell button
- [ ] **UI-10**: AI chat panel with message input, scrolling history, loading indicator
- [ ] **UI-11**: Inline trade and watchlist action confirmations rendered in chat messages
- [ ] **UI-12**: Header with live portfolio total value, cash balance, and connection status dot

### Infrastructure

- [ ] **INFRA-01**: Multi-stage Dockerfile (latest stable Node → latest stable Python)
- [ ] **INFRA-02**: Start/stop shell scripts for macOS/Linux
- [ ] **INFRA-03**: Start/stop PowerShell scripts for Windows
- [x] **INFRA-04**: Health check endpoint (GET /api/health)

### Testing

- [ ] **TEST-01**: Backend unit tests for trade execution logic and edge cases
- [ ] **TEST-02**: Backend unit tests for LLM structured output parsing
- [ ] **TEST-03**: Frontend unit tests for key components (price flash, portfolio display)
- [ ] **TEST-04**: E2E tests with Playwright using LLM mock mode

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Enhancements

- **ENH-01**: Portfolio reset functionality
- **ENH-02**: Multiple watchlists
- **ENH-03**: Technical indicators on charts
- **ENH-04**: Cloud deployment (Terraform / AWS App Runner)

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| User authentication / multi-user | Single-user demo app; hardcoded "default" user |
| Limit orders / order book | Market orders only — eliminates order book complexity |
| Real money trading | Simulated only; $10k virtual cash, zero stakes |
| Options / futures / crypto | Equities only; each asset class adds pricing complexity |
| Streaming LLM responses (SSE for chat) | Structured output requires complete JSON; loading indicator sufficient |
| Persistent chart data across sessions | Simulator generates random walks; historical data meaningless across restarts |
| Mobile-first design | Trading terminals are data-dense; desktop-first, functional on tablet |
| WebSocket for bidirectional comms | SSE is simpler and sufficient for one-way push |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| DB-01 | Phase 1 | Complete |
| DB-02 | Phase 1 | Complete |
| DB-03 | Phase 1 | Complete |
| DB-04 | Phase 1 | Complete |
| WATCH-01 | Phase 2 | Complete |
| WATCH-02 | Phase 2 | Complete |
| WATCH-03 | Phase 2 | Complete |
| PORT-01 | Phase 2 | Complete |
| PORT-02 | Phase 2 | Complete |
| PORT-03 | Phase 2 | Complete |
| PORT-04 | Phase 2 | Complete |
| PORT-05 | Phase 2 | Complete |
| PORT-06 | Phase 2 | Pending |
| PORT-07 | Phase 2 | Pending |
| CHAT-01 | Phase 3 | Pending |
| CHAT-02 | Phase 3 | Pending |
| CHAT-03 | Phase 3 | Pending |
| CHAT-04 | Phase 3 | Pending |
| CHAT-05 | Phase 3 | Pending |
| CHAT-06 | Phase 3 | Pending |
| UI-01 | Phase 4 | Pending |
| UI-02 | Phase 4 | Pending |
| UI-03 | Phase 4 | Pending |
| UI-04 | Phase 4 | Pending |
| UI-05 | Phase 4 | Pending |
| UI-06 | Phase 4 | Pending |
| UI-07 | Phase 4 | Pending |
| UI-08 | Phase 4 | Pending |
| UI-09 | Phase 4 | Pending |
| UI-10 | Phase 4 | Pending |
| UI-11 | Phase 4 | Pending |
| UI-12 | Phase 4 | Pending |
| INFRA-01 | Phase 5 | Pending |
| INFRA-02 | Phase 5 | Pending |
| INFRA-03 | Phase 5 | Pending |
| INFRA-04 | Phase 2 | Complete |
| TEST-01 | Phase 6 | Pending |
| TEST-02 | Phase 6 | Pending |
| TEST-03 | Phase 6 | Pending |
| TEST-04 | Phase 6 | Pending |

**Coverage:**
- v1 requirements: 40 total
- Mapped to phases: 40
- Unmapped: 0

---
*Requirements defined: 2026-03-16*
*Last updated: 2026-03-16 after roadmap creation*
