# FinAlly — AI Trading Workstation

## What This Is

FinAlly (Finance Ally) is a visually stunning AI-powered trading workstation that streams live market data, lets users trade a simulated portfolio, and integrates an LLM chat assistant that can analyze positions and execute trades on the user's behalf. It looks and feels like a modern Bloomberg terminal with an AI copilot. Built as the capstone project for an agentic AI coding course, demonstrating how orchestrated AI agents can produce a production-quality full-stack application.

## Core Value

Users can interact with a live-updating trading terminal where an AI assistant can analyze their portfolio and execute trades through natural language — demonstrating agentic AI capabilities in a visually impressive, zero-friction experience.

## Requirements

### Validated

<!-- Shipped and confirmed valuable. -->

- ✓ Market data simulator generates realistic prices via GBM with correlated moves — existing
- ✓ Massive (Polygon.io) REST API client for real market data — existing
- ✓ Unified MarketDataSource interface with runtime selection via environment variable — existing
- ✓ Thread-safe PriceCache with version-based change detection — existing
- ✓ SSE streaming endpoint pushes price updates every ~500ms — existing
- ✓ 10 default tickers with realistic seed prices and per-ticker parameters — existing

### Active

<!-- Current scope. Building toward these. -->

- [ ] Database layer with lazy initialization and schema/seed auto-creation
- [ ] Portfolio API — positions, cash balance, total value, unrealized P&L
- [ ] Trade execution — market orders, instant fill, validation (cash/shares)
- [ ] Portfolio history snapshots for P&L chart
- [ ] Watchlist CRUD API
- [ ] LLM chat integration via LiteLLM with Gemini structured outputs
- [ ] LLM auto-execution of trades and watchlist changes
- [ ] LLM mock mode for testing
- [ ] Dark trading terminal frontend with live-updating prices
- [ ] Price flash animations (green uptick, red downtick)
- [ ] Sparkline mini-charts accumulated from SSE stream
- [ ] Main chart area with ticker selection
- [ ] Portfolio heatmap (treemap) sized by weight, colored by P&L
- [ ] P&L line chart from portfolio snapshots
- [ ] Positions table with unrealized P&L
- [ ] Trade bar — ticker, quantity, buy/sell buttons
- [ ] AI chat panel with inline trade/watchlist confirmations
- [ ] Header with live portfolio value, cash balance, connection status
- [ ] Multi-stage Dockerfile (Node 20 → Python 3.12)
- [ ] Start/stop scripts for macOS/Linux and Windows
- [ ] Backend unit tests (portfolio, trade, LLM parsing)
- [ ] Frontend unit tests (components, price flash, portfolio display)
- [ ] E2E tests with Playwright

### Out of Scope

<!-- Explicit boundaries. -->

- User authentication/signup — single-user app, hardcoded "default" user
- Real money trading — simulated only, $10k virtual cash
- Limit orders / order book — market orders only for simplicity
- Real-time chat (WebSocket) — SSE is sufficient for one-way push
- Mobile app — desktop-first web app
- Cloud deployment — Docker container runs locally (Terraform stretch goal only)
- Multi-user support — schema supports it but not implemented

## Context

- **Existing code**: Market data subsystem is complete and production-quality (66 tests, reviewed). Backend is a uv-managed FastAPI project. Frontend (Next.js) not yet scaffolded.
- **Stack**: Python 3.12+ / FastAPI backend, Next.js TypeScript static export frontend, SQLite database, SSE for real-time data, LiteLLM → Gemini for AI chat.
- **Design**: Dark Bloomberg terminal aesthetic. Colors: accent yellow `#ecad0a`, blue primary `#209dd7`, purple secondary `#753991`. Backgrounds around `#0d1117`.
- **Course context**: This is a capstone project for an agentic AI coding course. The app itself is built by AI agents to demonstrate the concept.

## Constraints

- **Single container**: One Docker container, one port (8000), no docker-compose for production
- **Package manager**: uv for Python, npm for Node — always `uv run`, never `python3` directly
- **No CORS**: Static Next.js export served by FastAPI on same origin
- **SQLite only**: No database server — self-contained, zero config
- **Market orders only**: No order book complexity, instant fill at current price
- **LLM model**: LiteLLM with `gemini/gemini-3.1-flash-lite-preview` and structured outputs

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| SSE over WebSockets | One-way push is all we need; simpler, universal browser support | ✓ Good — implemented in market data |
| Static Next.js export | Single origin, no CORS, one port, one container | — Pending |
| SQLite over Postgres | No multi-user = no need for DB server; self-contained | — Pending |
| Market orders only | Eliminates order book, limit orders, partial fills | — Pending |
| LLM auto-executes trades | Zero-stakes demo environment; impressive agentic demo | — Pending |
| Lightweight Charts for charting | Canvas-based, performant for streaming data | — Pending |

---
*Last updated: 2026-03-16 after initialization*
