# Feature Research

**Domain:** AI-powered simulated trading workstation (Bloomberg-inspired terminal with AI copilot)
**Researched:** 2026-03-16
**Confidence:** HIGH

## Feature Landscape

### Table Stakes (Users Expect These)

Features users assume exist. Missing these = product feels incomplete or broken.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Live-updating price feed | Every trading terminal streams prices in real-time; static prices = broken product | MEDIUM | Already built (SSE streaming via market data subsystem). Frontend must connect and display. |
| Watchlist with add/remove | Bloomberg, TradingView, every broker has this. Users need to track their picks. | LOW | CRUD API + frontend list component. 10 default tickers seeded. |
| Price flash animations (green/red) | Visual feedback on uptick/downtick is the defining UX of a trading terminal. Without it, prices look static. | LOW | CSS transition on price change — brief background highlight fading over ~500ms. |
| Buy/sell trade execution | A trading platform where you cannot trade is not a trading platform. | MEDIUM | Market orders only (deliberate simplification). Validation: cash check, share check, quantity > 0. |
| Positions table with P&L | Users need to see what they own, what they paid, and whether they are up or down. | LOW | Read from positions + live prices. Columns: ticker, qty, avg cost, current price, unrealized P&L, % change. |
| Cash balance display | Users must know how much buying power they have. | LOW | Read from user profile, update after trades. Show in header. |
| Portfolio total value (live) | The single most important number — "how am I doing?" Must update as prices stream. | LOW | Sum of (position qty * current price) + cash. Update on each SSE tick. |
| Dark theme terminal aesthetic | The plan specifies Bloomberg-inspired look. A light theme would feel wrong for this product category. | MEDIUM | Tailwind dark theme with custom palette. Backgrounds ~#0d1117, accent yellow/blue/purple. |
| Connection status indicator | Users need to know if their data feed is live. Without this, stale prices look real. | LOW | Small colored dot in header: green=connected, yellow=reconnecting, red=disconnected. |
| Trade history / activity log | Users expect to see a record of what they have done. Every broker has this. | LOW | Read from trades table. Show ticker, side, qty, price, timestamp. |
| Health check endpoint | Required for Docker container management and deployment verification. | LOW | GET /api/health returning status. |

### Differentiators (Competitive Advantage)

Features that set FinAlly apart from a generic paper trading app. These are what make the demo impressive.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| AI chat assistant with portfolio awareness | The core differentiator. An LLM that knows your positions, cash, and live prices — and can reason about them. No paper trading app has this built in. | HIGH | LiteLLM + Gemini structured outputs. System prompt injects portfolio context + last 10 messages. |
| AI auto-execution of trades | The "wow factor" — tell the AI to buy something and it does it. No confirmation dialog. Demonstrates agentic AI in a zero-stakes environment. | HIGH | LLM returns structured JSON with trades array; backend auto-executes through same trade validation pipeline. |
| AI watchlist management | Natural language control: "add PYPL to my watchlist" or "remove TSLA". Fluid, conversational. | MEDIUM | Structured output includes watchlist_changes array. Backend processes add/remove actions. |
| Inline action confirmations in chat | When the AI executes a trade or modifies the watchlist, the chat shows what happened — not just the text response. Makes the AI feel like it actually did something. | MEDIUM | Frontend renders the `actions` JSON from chat_messages as visual confirmation cards. |
| Portfolio heatmap (treemap) | Visually striking. Rectangles sized by weight, colored by P&L. Bloomberg has this. Most paper trading apps do not. | MEDIUM | Use a treemap library (d3-based or lightweight alternative). Data from positions + live prices. |
| Sparkline mini-charts in watchlist | Adds visual density that distinguishes a terminal from a simple table. Accumulated from SSE since page load — they fill in progressively, which is visually satisfying. | MEDIUM | Canvas-based sparklines built from price history array per ticker, appended on each SSE event. |
| Main chart area (ticker detail) | Click a watchlist ticker to see a larger price-over-time chart. Gives the app depth — not just a flat list. | MEDIUM | Lightweight Charts (canvas-based). Price data accumulated from SSE since page load for selected ticker. |
| P&L chart over time | Line chart showing portfolio value trajectory. Uses backend snapshots (every 30s + post-trade). Tells the story of how the session went. | MEDIUM | Lightweight Charts line series. Data from GET /api/portfolio/history. |
| Zero-friction first launch | No signup, no login, no config. Docker run + browser open = instant terminal. $10k virtual cash, 10 default tickers, AI ready. This is critical for a course capstone demo. | LOW | Lazy DB init, default seed data, single container, start scripts. |
| LLM mock mode for testing | Enables deterministic E2E tests without API keys. Also allows development without a Google API key. | LOW | Backend returns canned responses when LLM_MOCK=true. |

### Anti-Features (Commonly Requested, Often Problematic)

Features that seem good but would hurt this specific project.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Limit orders / order book | "Real trading has limit orders" | Adds order book state machine, partial fills, order lifecycle, cancellation logic. Massive complexity for a demo app. Market orders are instant and simple. | Market orders only. Instant fill at current price. The plan explicitly scopes this out. |
| User authentication / multi-user | "What if multiple people use it?" | Single-user is a deliberate constraint. Auth adds sessions, JWT/cookies, registration UI, password management. All irrelevant to the AI demo. | Hardcoded "default" user. Schema has user_id for future-proofing but no auth layer. |
| Real money trading | "Make it a real broker" | Regulatory, legal, security, compliance nightmare. Completely out of scope. | Simulated trading with $10k virtual cash. Zero stakes = AI can auto-execute freely. |
| Technical indicators (RSI, MACD, Bollinger) | "Every charting platform has indicators" | Significant charting complexity. Requires indicator calculation engine, UI for adding/removing/configuring. Not the point of this demo. | Simple price-over-time charts. The AI assistant can verbally discuss indicators. |
| Options / futures / crypto | "Support more asset classes" | Each asset class has different pricing models, contract specs, expiration logic. Enormous scope expansion. | Equities only (stocks). 10 default tickers covering tech, finance, media. |
| Streaming chat (SSE for LLM responses) | "Token-by-token streaming looks cool" | Structured output parsing requires the complete JSON response. Streaming would mean parsing partial JSON or switching to unstructured text. Adds complexity to both backend and frontend. | Complete JSON response. Show loading indicator while waiting. Response is fast with Flash Lite. |
| Persistent chart data across sessions | "I want to see yesterday's prices" | Requires storing full price history in the database. The simulator generates random walks so historical data is meaningless across restarts. | Charts accumulate from SSE since page load. Fresh session = fresh charts. This is appropriate for a demo. |
| Mobile-first responsive design | "It should work on phones" | Trading terminals are data-dense by nature. Phone screens cannot show a watchlist, chart, heatmap, positions, and chat simultaneously. | Desktop-first. Functional on tablet. Phone is explicitly out of scope. |
| WebSocket for bidirectional communication | "WebSockets are more modern" | SSE is simpler, has built-in browser reconnection, and one-way push is all this app needs. No client-to-server streaming required. | SSE (EventSource API). Already implemented in market data subsystem. |
| Portfolio reset / multiple portfolios | "Let me start over" or "Let me try different strategies" | Adds UI complexity and backend logic for portfolio lifecycle management. | Single portfolio. Users can sell all positions manually or ask the AI to do it. Docker volume can be deleted for a full reset. |

## Feature Dependencies

```
[Market Data Subsystem] (COMPLETE)
    |
    +--provides prices to--> [SSE Streaming] (COMPLETE)
    |                            |
    |                            +--feeds--> [Watchlist UI] (price display)
    |                            +--feeds--> [Sparkline Charts]
    |                            +--feeds--> [Main Chart Area]
    |                            +--feeds--> [Portfolio Value Calculation]
    |                            +--feeds--> [Positions Table] (current price column)
    |
    +--provides prices to--> [Trade Execution] (fill price)

[Database Schema + Lazy Init]
    |
    +--required by--> [Watchlist CRUD API]
    +--required by--> [Portfolio API] (positions, cash)
    +--required by--> [Trade Execution]
    +--required by--> [Portfolio Snapshots]
    +--required by--> [Chat History Storage]

[Watchlist CRUD API]
    +--required by--> [Watchlist UI]
    +--required by--> [AI Watchlist Management]

[Portfolio API]
    +--required by--> [Positions Table]
    +--required by--> [Portfolio Heatmap]
    +--required by--> [P&L Chart]
    +--required by--> [AI Portfolio Context] (injected into LLM prompt)

[Trade Execution]
    +--required by--> [Trade Bar UI]
    +--required by--> [AI Auto-Execution]
    +--triggers--> [Portfolio Snapshot] (post-trade)

[AI Chat Integration] (LiteLLM + Gemini)
    +--requires--> [Portfolio API] (for context injection)
    +--requires--> [Trade Execution] (for auto-execution)
    +--requires--> [Watchlist CRUD API] (for watchlist changes)
    +--requires--> [Chat History Storage] (for conversation continuity)
    +--required by--> [AI Chat Panel UI]

[Frontend Shell] (Next.js scaffold + layout + dark theme)
    +--required by--> ALL frontend components
```

### Dependency Notes

- **Database must come before any API work:** Every API endpoint reads from or writes to SQLite. The schema and lazy init are the foundation.
- **Portfolio API requires trade execution for live data:** Positions only exist after trades. But the API can return empty positions initially.
- **AI chat requires everything else first:** The LLM needs portfolio context (positions, cash, prices) and the ability to execute trades and modify the watchlist. It is the integration layer that ties all features together.
- **Frontend shell must exist before any UI feature:** The Next.js scaffold, dark theme, layout grid, and SSE connection are prerequisites for all visual components.
- **Sparklines and main chart share the SSE price accumulation pattern:** Both need the frontend to maintain a per-ticker price history array from SSE events. Build this once, use in both.

## MVP Definition

### Launch With (v1)

Minimum viable product — the smallest thing that demonstrates "AI trading workstation."

- [ ] Database layer with lazy init, schema, seed data -- foundation for everything
- [ ] Watchlist CRUD API + UI with live prices and flash animations -- the "alive" feeling
- [ ] Portfolio API + trade execution + positions table -- users can trade and see results
- [ ] Trade bar (ticker, qty, buy/sell) -- manual trade entry
- [ ] Cash balance + portfolio total value in header -- essential status info
- [ ] Main chart area (click ticker to see price chart) -- visual depth
- [ ] AI chat with portfolio awareness + auto-execution -- the differentiator
- [ ] Dark terminal theme + layout -- the aesthetic promise
- [ ] Docker container with start scripts -- zero-friction launch

### Add After Validation (v1.x)

Features to add once the core loop (stream prices, trade, chat with AI) works end-to-end.

- [ ] Sparkline mini-charts in watchlist -- visual polish, depends on price accumulation pattern
- [ ] Portfolio heatmap (treemap) -- impressive visualization but not blocking core functionality
- [ ] P&L chart from portfolio snapshots -- requires snapshot background task
- [ ] Inline action confirmations in chat -- polish the AI chat UX
- [ ] Trade history view -- nice-to-have audit trail
- [ ] LLM mock mode -- needed for E2E tests but not for initial demo

### Future Consideration (v2+)

Features to defer until the product is fully working.

- [ ] E2E tests with Playwright -- important for quality but not for first demo
- [ ] Frontend unit tests -- important for maintenance, defer until components stabilize
- [ ] Cloud deployment (Terraform / App Runner) -- stretch goal per PLAN.md

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Database layer + lazy init | HIGH (blocks everything) | MEDIUM | P1 |
| Watchlist CRUD API | HIGH | LOW | P1 |
| Portfolio API (positions, cash, value) | HIGH | MEDIUM | P1 |
| Trade execution (market orders) | HIGH | MEDIUM | P1 |
| SSE price display in watchlist UI | HIGH | LOW | P1 |
| Price flash animations | HIGH (terminal feel) | LOW | P1 |
| Trade bar UI | HIGH | LOW | P1 |
| Positions table with live P&L | HIGH | LOW | P1 |
| Header (value, cash, connection status) | HIGH | LOW | P1 |
| Dark terminal theme + layout | HIGH (aesthetic promise) | MEDIUM | P1 |
| Main chart area | MEDIUM | MEDIUM | P1 |
| AI chat with portfolio context | HIGH (differentiator) | HIGH | P1 |
| AI auto-execution of trades | HIGH (wow factor) | HIGH | P1 |
| AI watchlist management | MEDIUM | LOW | P1 |
| Sparkline mini-charts | MEDIUM | MEDIUM | P2 |
| Portfolio heatmap (treemap) | MEDIUM | MEDIUM | P2 |
| P&L chart (portfolio history) | MEDIUM | MEDIUM | P2 |
| Portfolio snapshot background task | MEDIUM (enables P&L chart) | LOW | P2 |
| Inline chat action confirmations | MEDIUM | LOW | P2 |
| Trade history view | LOW | LOW | P2 |
| LLM mock mode | MEDIUM (enables testing) | LOW | P2 |
| Docker multi-stage build | HIGH (delivery) | MEDIUM | P1 |
| Start/stop scripts | HIGH (zero-friction) | LOW | P1 |
| Backend unit tests | MEDIUM | MEDIUM | P2 |
| Frontend unit tests | MEDIUM | MEDIUM | P3 |
| E2E tests (Playwright) | MEDIUM | HIGH | P3 |

**Priority key:**
- P1: Must have for launch -- core trading loop + AI chat + delivery mechanism
- P2: Should have, add when core works -- visual polish, testing, secondary features
- P3: Nice to have, future consideration -- comprehensive test suites, deployment

## Competitor Feature Analysis

| Feature | Bloomberg Terminal | TradingView | Paper Trading Apps (Webull, thinkorswim) | FinAlly Approach |
|---------|-------------------|-------------|------------------------------------------|------------------|
| Live prices | Real-time feeds, custom keyboard | Real-time with delays on free tier | Real-time or delayed | SSE streaming, simulated or real (Massive API) |
| Watchlist | Multiple lists, deep customization | Multiple lists, sorting, filtering | Basic list | Single list, add/remove, live prices + sparklines |
| Charting | Hundreds of chart types, indicators | 400+ indicators, 110+ drawing tools | Full charting suites | Simple price-over-time. Lightweight Charts. No indicators. |
| Portfolio view | Multi-account, risk analytics, attribution | Via broker integration | Positions, P&L, history | Positions table, heatmap, P&L chart, cash balance |
| Trade execution | Full order types, algos, dark pools | Via connected broker | Full order types | Market orders only. Instant fill. Zero fees. |
| AI assistant | None built-in (uses separate tools) | None built-in | None built-in | LLM chat with auto-execution -- unique differentiator |
| Heatmap/treemap | Yes (sector, market cap) | Yes (market overview) | No | Portfolio-level treemap (positions by weight, colored by P&L) |
| Dark theme | Iconic dark terminal | Dark mode available | Varies | Mandatory. Bloomberg-inspired. Custom palette. |
| Setup friction | Hardware + $24k/year subscription | Account registration | Account registration | Zero. Docker run. No account. |

## Sources

- [Bloomberg Terminal Features & Pricing (SoftwareAdvice)](https://www.softwareadvice.com/accounting/bloomberg-terminal-profile/)
- [Bloomberg Terminal (Wikipedia)](https://en.wikipedia.org/wiki/Bloomberg_Terminal)
- [Best AI for Stock Trading 2026 (Monday.com)](https://monday.com/blog/ai-agents/best-ai-for-stock-trading/)
- [Best Paper Trading Platforms 2026 (StockBrokers.com)](https://www.stockbrokers.com/guides/paper-trading)
- [Paper Trading Platform Standard 2025 (ETNA)](https://www.etnasoft.com/best-paper-trading-platform-for-u-s-broker-dealers-why-advanced-simulation-sets-the-2025-standard/)
- [TradingView Features](https://www.tradingview.com/features/)
- [TradingView Review 2026 (StockBrokers.com)](https://www.stockbrokers.com/review/tools/tradingview)
- [Trading Platform Design Examples 2026 (Merge)](https://merge.rocks/blog/the-10-best-trading-platform-design-examples-in-2024)
- [Stock Market Heatmaps Guide (Bookmap)](https://bookmap.com/blog/heatmap-in-trading-the-complete-guide-to-market-depth-visualization)

---
*Feature research for: AI-powered simulated trading workstation*
*Researched: 2026-03-16*
