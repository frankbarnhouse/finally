# Market Data Component — Summary

The market data subsystem is complete and reviewed. This document summarises the four source documents now archived in `planning/archive/`.

## Architecture

A unified `MarketDataSource` interface with two implementations selected at runtime by the `MASSIVE_API_KEY` environment variable:

- **SimulatorDataSource** (default) — generates prices via Geometric Brownian Motion (GBM) with correlated moves (Cholesky decomposition) and random shock events. Ticks every 500ms.
- **MassiveDataSource** (optional) — polls the Massive (Polygon.io) REST API every 15 seconds using `asyncio.to_thread()` to avoid blocking the event loop.

Both write to a shared, thread-safe **PriceCache** (one writer, many readers). All downstream consumers (SSE streaming, portfolio valuation, trade execution) read from the cache and are source-agnostic.

## Key Components

| Module | Purpose |
|---|---|
| `models.py` | `PriceUpdate` frozen dataclass (ticker, price, previous price, direction, change) |
| `cache.py` | `PriceCache` — thread-safe in-memory store with monotonic version counter |
| `interface.py` | `MarketDataSource` ABC (start, stop, add/remove ticker) |
| `factory.py` | Selects implementation from environment variable |
| `simulator.py` | `GBMSimulator` math engine + `SimulatorDataSource` async wrapper |
| `massive_client.py` | `MassiveDataSource` — REST polling via Massive Python client |
| `seed_prices.py` | Default tickers, realistic seed prices, per-ticker volatility/drift params |
| `stream.py` | SSE endpoint (`GET /api/stream/prices`) pushing updates every ~500ms |

## Simulator Details

- GBM formula with Ito correction: `S(t+dt) = S(t) * exp((mu - 0.5*sigma^2)*dt + sigma*sqrt(dt)*Z)`
- Correlated moves across sectors (tech 0.6, finance 0.5, cross-sector 0.3, TSLA 0.3)
- Random events: ~0.1% chance per tick per ticker of a 2-5% shock
- 10 default tickers: AAPL, GOOGL, MSFT, AMZN, TSLA, NVDA, META, JPM, V, NFLX

## Code Review Outcome (2026-03-14)

Rated **production-quality for this demo**. 66 tests across 6 test files, all expected to pass. Three minor bugs were identified and fixed:

1. `stream.py` — global router mutated by factory (fixed: create router inside factory)
2. `massive_client.py` — `start()` missing ticker normalization (fixed: added `.upper().strip()`)
3. `simulator.py` — `add_ticker()` missing case normalization (fixed)

## Source Documents

Archived to `planning/archive/`:
- `MARKET_DATA_DESIGN.md` — full implementation-ready design (1375 lines)
- `MARKET_INTERFACE.md` — unified interface, types, module layout
- `MARKET_SIMULATOR.md` — GBM math, correlation model, seed data
- `MARKET_DATA_REVIEW.md` — code review with bug findings and test assessment
