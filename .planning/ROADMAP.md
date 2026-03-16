# Roadmap: FinAlly — AI Trading Workstation

## Overview

FinAlly is a brownfield project with a complete market data subsystem (simulator, Massive client, SSE streaming, PriceCache). The remaining work builds upward from a database foundation through backend APIs, LLM integration, a full trading terminal frontend, and finally Docker packaging and testing. Each phase delivers a coherent, verifiable capability that unblocks the next.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Database Foundation** - SQLite layer with lazy init, schema creation, seed data, and WAL mode (completed 2026-03-16)
- [x] **Phase 2: Portfolio and Watchlist APIs** - Trade execution, positions, watchlist CRUD, portfolio snapshots, health check (completed 2026-03-16)
- [ ] **Phase 3: LLM Chat Integration** - AI assistant with portfolio context, structured outputs, auto-execution, and mock mode
- [ ] **Phase 4: Trading Terminal Frontend** - Dark Bloomberg-inspired UI with live prices, charts, portfolio visualizations, trade bar, and chat panel
- [ ] **Phase 5: Docker and Scripts** - Multi-stage Dockerfile, start/stop scripts, single-container deployment
- [ ] **Phase 6: Testing** - Backend unit tests, frontend unit tests, Playwright E2E tests

## Phase Details

### Phase 1: Database Foundation
**Goal**: The backend has a working persistence layer that auto-initializes on first use
**Depends on**: Nothing (first phase; builds on existing market data subsystem)
**Requirements**: DB-01, DB-02, DB-03, DB-04
**Success Criteria** (what must be TRUE):
  1. Starting the backend with no existing database file creates all 6 tables and seeds default data automatically
  2. The default user profile exists with $10,000 cash balance after initialization
  3. The default watchlist contains exactly 10 tickers (AAPL, GOOGL, MSFT, AMZN, TSLA, NVDA, META, JPM, V, NFLX) after initialization
  4. SQLite is configured with WAL mode and busy_timeout so concurrent async operations do not produce "database is locked" errors
**Plans:** 1/1 plans complete

Plans:
- [ ] 01-01-PLAN.md — SQLite module with lazy init, schema, seed data, WAL config, and tests

### Phase 2: Portfolio and Watchlist APIs
**Goal**: Users can trade, view positions, manage their watchlist, and the system records portfolio history
**Depends on**: Phase 1
**Requirements**: PORT-01, PORT-02, PORT-03, PORT-04, PORT-05, PORT-06, PORT-07, WATCH-01, WATCH-02, WATCH-03, INFRA-04
**Success Criteria** (what must be TRUE):
  1. User can view all positions with current prices, cash balance, total portfolio value, and unrealized P&L via GET /api/portfolio
  2. User can buy shares (cash decreases, position appears or updates) and sell shares (cash increases, position updates or disappears) at the current market price
  3. Attempting to buy with insufficient cash or sell more shares than owned returns a clear error message
  4. User can view, add, and remove tickers from their watchlist, and the watchlist reflects in the SSE price stream
  5. Portfolio value snapshots are recorded every 30 seconds and immediately after each trade, retrievable for charting
**Plans:** 3/3 plans complete

Plans:
- [ ] 02-01-PLAN.md — Portfolio service layer and trade execution API (GET /api/portfolio, POST /api/portfolio/trade)
- [ ] 02-02-PLAN.md — Watchlist CRUD API and health check endpoint
- [ ] 02-03-PLAN.md — Portfolio snapshots, history endpoint, and FastAPI app wiring

### Phase 3: LLM Chat Integration
**Goal**: Users can converse with an AI assistant that understands their portfolio and can execute trades and manage the watchlist through natural language
**Depends on**: Phase 2
**Requirements**: CHAT-01, CHAT-02, CHAT-03, CHAT-04, CHAT-05, CHAT-06
**Success Criteria** (what must be TRUE):
  1. User can send a chat message and receive an AI response that references their current portfolio state (positions, cash, P&L)
  2. When the user asks the AI to buy or sell, the trade executes automatically and the updated position/cash is reflected
  3. When the user asks the AI to add or remove a watchlist ticker, the change happens automatically
  4. If an AI-initiated trade or watchlist action fails validation, the failure reason appears in the response message text
  5. Setting LLM_MOCK=true produces deterministic responses without calling any external API
**Plans**: TBD

Plans:
- [ ] 03-01: TBD
- [ ] 03-02: TBD

### Phase 4: Trading Terminal Frontend
**Goal**: Users see a visually stunning, live-updating trading terminal in the browser with all panels operational
**Depends on**: Phase 2 (API contracts stable); Phase 3 (chat API available)
**Requirements**: UI-01, UI-02, UI-03, UI-04, UI-05, UI-06, UI-07, UI-08, UI-09, UI-10, UI-11, UI-12
**Success Criteria** (what must be TRUE):
  1. Opening the app in a browser shows a dark, data-dense trading terminal layout with prices streaming and updating live from the SSE feed
  2. Price changes flash green (uptick) or red (downtick) with a fade animation, and each watchlist ticker shows a sparkline mini-chart that fills in progressively
  3. Clicking a ticker in the watchlist displays a larger price chart in the main chart area
  4. The portfolio section shows a heatmap (treemap) of positions colored by P&L, a P&L line chart of portfolio value over time, and a positions table with unrealized P&L
  5. The trade bar allows buying and selling shares, the chat panel allows conversing with the AI (with inline action confirmations), and the header displays live portfolio value, cash balance, and connection status
**Plans**: TBD

Plans:
- [ ] 04-01: TBD
- [ ] 04-02: TBD
- [ ] 04-03: TBD
- [ ] 04-04: TBD

### Phase 5: Docker and Scripts
**Goal**: Users can launch the entire application with a single Docker command or shell script
**Depends on**: Phase 4 (frontend build output needed for multi-stage Docker build)
**Requirements**: INFRA-01, INFRA-02, INFRA-03
**Success Criteria** (what must be TRUE):
  1. Running the start script builds (if needed) and launches a single Docker container serving the app on port 8000
  2. The app is fully functional inside the container — prices stream, trades execute, chat works, all UI panels render
  3. Stopping and restarting the container preserves the SQLite database (portfolio state, trade history, chat history) via Docker volume
**Plans**: TBD

Plans:
- [ ] 05-01: TBD

### Phase 6: Testing
**Goal**: Core functionality is covered by automated tests that catch regressions
**Depends on**: Phase 5 (E2E tests need Docker stack; unit tests can reference earlier phases)
**Requirements**: TEST-01, TEST-02, TEST-03, TEST-04
**Success Criteria** (what must be TRUE):
  1. Backend unit tests verify trade execution logic including edge cases (insufficient cash, insufficient shares, full position close, fractional shares)
  2. Backend unit tests verify LLM structured output parsing handles valid schemas, malformed responses, and failed action reporting
  3. Frontend unit tests verify key component behaviors (price flash animation triggers, portfolio display calculations)
  4. Playwright E2E tests run against the Docker container with LLM_MOCK=true and verify core user flows (prices streaming, watchlist CRUD, buy/sell, chat interaction)
**Plans**: TBD

Plans:
- [ ] 06-01: TBD
- [ ] 06-02: TBD
- [ ] 06-03: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3 -> 4 -> 5 -> 6

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Database Foundation | 1/1 | Complete    | 2026-03-16 |
| 2. Portfolio and Watchlist APIs | 0/3 | Complete    | 2026-03-16 |
| 3. LLM Chat Integration | 0/2 | Not started | - |
| 4. Trading Terminal Frontend | 0/4 | Not started | - |
| 5. Docker and Scripts | 0/1 | Not started | - |
| 6. Testing | 0/3 | Not started | - |
