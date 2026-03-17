# FinAlly — AI Trading Workstation

## What This Is

FinAlly (Finance Ally) is an AI-powered trading workstation that streams live market data, lets users trade a simulated portfolio, and integrates an LLM chat assistant that can analyze positions and execute trades through natural language. It looks and feels like a modern Bloomberg terminal with an AI copilot. Built as the capstone project for an agentic AI coding course, demonstrating how orchestrated AI agents can produce a production-quality full-stack application.

## Core Value

Users can interact with a live-updating trading terminal where an AI assistant can analyze their portfolio and execute trades through natural language — demonstrating agentic AI capabilities in a visually impressive, zero-friction experience.

## Requirements

### Validated

<!-- Shipped and confirmed valuable. -->

- ✓ Market data simulator with GBM, correlated moves, and random events — v1.0
- ✓ Massive (Polygon.io) REST API client for real market data — v1.0
- ✓ Unified MarketDataSource interface with runtime selection — v1.0
- ✓ Thread-safe PriceCache with version-based change detection — v1.0
- ✓ SSE streaming endpoint pushing price updates every ~500ms — v1.0
- ✓ SQLite database with lazy init, 6-table schema, WAL mode, auto-seeding — v1.0
- ✓ Portfolio API with positions, cash balance, total value, unrealized P&L — v1.0
- ✓ Trade execution with BEGIN IMMEDIATE transactions, validation — v1.0
- ✓ Portfolio snapshots (30s periodic + post-trade) — v1.0
- ✓ Watchlist CRUD API with position-aware removal — v1.0
- ✓ LLM chat via LiteLLM + Gemini with structured outputs — v1.0
- ✓ LLM auto-execution of trades and watchlist changes — v1.0
- ✓ LLM mock mode for deterministic testing — v1.0
- ✓ Dark Bloomberg-inspired trading terminal with live SSE prices — v1.0
- ✓ Price flash animations, sparklines, main chart, portfolio heatmap — v1.0
- ✓ Trade bar, AI chat panel with inline action confirmations — v1.0
- ✓ Multi-stage Dockerfile with start/stop scripts — v1.0
- ✓ Backend tests (127+), frontend tests (24), E2E scenarios (8) — v1.0

### Active

<!-- Current scope. Building toward these. -->

(None — v1.0 shipped, next milestone not yet defined)

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

- **Shipped v1.0** with ~5,700 LOC across Python backend and TypeScript frontend
- **Stack**: Python 3.12 / FastAPI backend, Next.js 15 TypeScript static export, SQLite, SSE, LiteLLM → Gemini, Tailwind v4, Zustand, Lightweight Charts, d3-hierarchy
- **Design**: Dark Bloomberg terminal aesthetic. Colors: accent yellow `#ecad0a`, blue primary `#209dd7`, purple secondary `#753991`
- **Tests**: 127+ backend pytest tests, 24 frontend vitest tests, 8 Playwright E2E scenarios
- **Course context**: Capstone project for an agentic AI coding course, built entirely by AI agents

## Constraints

- **Latest stable versions**: Use latest stable Node.js, Next.js, and Python
- **Single container**: One Docker container, one port (8000)
- **Package manager**: uv for Python, npm for Node
- **No CORS**: Static Next.js export served by FastAPI on same origin
- **SQLite only**: No database server
- **Market orders only**: Instant fill at current price
- **LLM model**: LiteLLM with `gemini/gemini-3.1-flash-lite-preview`

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| SSE over WebSockets | One-way push; simpler, universal browser support | ✓ Good |
| Static Next.js export | Single origin, no CORS, one port, one container | ✓ Good |
| SQLite over Postgres | Single-user = no need for DB server; self-contained | ✓ Good |
| Market orders only | Eliminates order book complexity | ✓ Good |
| LLM auto-executes trades | Zero-stakes demo; impressive agentic demo | ✓ Good |
| Lightweight Charts | Canvas-based, performant for streaming data | ✓ Good |
| Zustand over Context | Selector-based subscriptions avoid re-render cascades from SSE | ✓ Good |
| d3-hierarchy for treemap | 30KB lightweight, React SVG rendering | ✓ Good |
| BEGIN IMMEDIATE transactions | Prevents TOCTOU race conditions on trade execution | ✓ Good |
| Service-layer separation | Portfolio/watchlist services reusable by both API routes and LLM chat | ✓ Good |

---
*Last updated: 2026-03-17 after v1.0 milestone*
