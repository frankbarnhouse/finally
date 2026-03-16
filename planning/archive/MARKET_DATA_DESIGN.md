# Market Data Backend — Detailed Design

This document provides a comprehensive, implementation-ready design for the FinAlly market data subsystem. It covers the unified interface, the GBM simulator, the Massive API client, the shared price cache, SSE streaming, and how all components integrate with the FastAPI application lifecycle.

---

## 1. Architecture Overview

```
                          ┌─────────────────────────────┐
                          │       FastAPI Lifespan       │
                          │                              │
                          │  startup:                    │
                          │    cache = PriceCache()      │
                          │    source = factory(cache)    │
                          │    await source.start(...)   │
                          │                              │
                          │  shutdown:                   │
                          │    await source.stop()       │
                          └──────────┬──────────────────┘
                                     │
                    ┌────────────────┴────────────────┐
                    │       MASSIVE_API_KEY set?       │
                    ├────── yes ──────┬──── no ───────┤
                    ▼                 │               ▼
          MassiveDataSource          │     SimulatorDataSource
          (polls REST API            │     (GBM ticks every
           every 15s)               │      500ms)
                    │                │               │
                    └────────────────┴───────────────┘
                                     │
                                     ▼
                              ┌─────────────┐
                              │  PriceCache  │  Thread-safe, in-memory
                              │  (single     │  One writer, many readers
                              │   instance)  │
                              └──────┬──────┘
                                     │
                    ┌────────────────┼────────────────┐
                    ▼                ▼                ▼
             SSE Streaming    Portfolio API     Trade Execution
             GET /api/        GET /api/         POST /api/
             stream/prices    portfolio         portfolio/trade
```

All downstream consumers read from `PriceCache` and are completely agnostic to whether prices come from the simulator or a real API.

---

## 2. Module Layout

```
backend/app/market/
├── __init__.py          # Public exports (5 symbols)
├── models.py            # PriceUpdate dataclass
├── cache.py             # PriceCache (thread-safe)
├── interface.py         # MarketDataSource ABC
├── factory.py           # Environment-driven factory
├── simulator.py         # GBMSimulator + SimulatorDataSource
├── massive_client.py    # MassiveDataSource (Polygon.io REST)
├── seed_prices.py       # Default tickers, prices, GBM params
└── stream.py            # SSE streaming router
```

---

## 3. Core Types

### 3.1 PriceUpdate — `app/market/models.py`

An immutable, frozen dataclass representing a single price observation. This is the fundamental unit of data flowing through the system.

```python
from __future__ import annotations
import time
from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class PriceUpdate:
    """Immutable snapshot of a single ticker's price at a point in time."""

    ticker: str
    price: float
    previous_price: float
    timestamp: float = field(default_factory=time.time)  # Unix seconds

    @property
    def change(self) -> float:
        """Absolute price change from previous update."""
        return round(self.price - self.previous_price, 4)

    @property
    def change_percent(self) -> float:
        """Percentage change from previous update."""
        if self.previous_price == 0:
            return 0.0
        return round(
            (self.price - self.previous_price) / self.previous_price * 100, 4
        )

    @property
    def direction(self) -> str:
        """'up', 'down', or 'flat'."""
        if self.price > self.previous_price:
            return "up"
        elif self.price < self.previous_price:
            return "down"
        return "flat"

    def to_dict(self) -> dict:
        """Serialize for JSON / SSE transmission."""
        return {
            "ticker": self.ticker,
            "price": self.price,
            "previous_price": self.previous_price,
            "timestamp": self.timestamp,
            "change": self.change,
            "change_percent": self.change_percent,
            "direction": self.direction,
        }
```

**Design decisions:**

- `frozen=True` — Immutability prevents accidental mutation by readers. Each price update is a new object.
- `slots=True` — Memory optimization. With 10+ tickers updating 2x/sec, thousands of these objects are created per session.
- `previous_price` is stored rather than computed — The cache holds the last `PriceUpdate`, so each new update can reference the prior price directly.
- Properties instead of fields for `change`, `change_percent`, `direction` — Computed on access, not stored. Keeps the object small and avoids stale derived data.

**SSE payload example:**

```json
{
  "ticker": "AAPL",
  "price": 191.23,
  "previous_price": 191.15,
  "timestamp": 1710432000.5,
  "change": 0.08,
  "change_percent": 0.0418,
  "direction": "up"
}
```

### 3.2 PriceCache — `app/market/cache.py`

Thread-safe in-memory store. One writer (the active data source), many readers (SSE stream, portfolio valuation, trade execution).

```python
from __future__ import annotations
import time
from threading import Lock
from .models import PriceUpdate


class PriceCache:
    def __init__(self) -> None:
        self._prices: dict[str, PriceUpdate] = {}
        self._lock = Lock()
        self._version: int = 0  # Monotonic counter, bumped on every update

    def update(self, ticker: str, price: float, timestamp: float | None = None) -> PriceUpdate:
        """Record a new price. Returns the created PriceUpdate.

        First update for a ticker: previous_price == price (direction='flat').
        Subsequent updates: previous_price is the last recorded price.
        Prices are rounded to 2 decimal places.
        """
        with self._lock:
            ts = timestamp or time.time()
            prev = self._prices.get(ticker)
            previous_price = prev.price if prev else price

            update = PriceUpdate(
                ticker=ticker,
                price=round(price, 2),
                previous_price=round(previous_price, 2),
                timestamp=ts,
            )
            self._prices[ticker] = update
            self._version += 1
            return update

    def get(self, ticker: str) -> PriceUpdate | None:
        """Get the latest price for a single ticker, or None if unknown."""
        with self._lock:
            return self._prices.get(ticker)

    def get_all(self) -> dict[str, PriceUpdate]:
        """Snapshot of all current prices. Returns a shallow copy."""
        with self._lock:
            return dict(self._prices)

    def get_price(self, ticker: str) -> float | None:
        """Convenience: get just the price float, or None."""
        update = self.get(ticker)
        return update.price if update else None

    def remove(self, ticker: str) -> None:
        """Remove a ticker from the cache."""
        with self._lock:
            self._prices.pop(ticker, None)

    @property
    def version(self) -> int:
        """Current version counter. Useful for SSE change detection."""
        return self._version
```

**Thread safety model:**

- A `threading.Lock` protects all reads and writes to `_prices` and `_version`.
- Why `threading.Lock` and not `asyncio.Lock`? The cache may be read from synchronous contexts (e.g., trade execution, portfolio valuation). A threading lock works in both sync and async code. The critical sections are extremely short (dict get/set), so contention is negligible.
- `_version` is a monotonic counter incremented on every `update()`. The SSE stream uses this for efficient change detection — it only serializes and sends data when the version has changed since the last push.

**Cache lifecycle:**

1. Created once during app startup
2. Passed to both the market data source (writer) and the SSE router (reader)
3. Also accessed by portfolio/trade endpoints for current price lookups
4. Lives for the entire app lifetime — no cleanup needed

---

## 4. MarketDataSource Interface — `app/market/interface.py`

The abstract base class that both implementations conform to.

```python
from __future__ import annotations
from abc import ABC, abstractmethod


class MarketDataSource(ABC):
    """Contract for market data providers.

    Implementations push price updates into a shared PriceCache on their own
    schedule. Downstream code never calls the data source directly for prices —
    it reads from the cache.
    """

    @abstractmethod
    async def start(self, tickers: list[str]) -> None:
        """Begin producing price updates for the given tickers.

        Starts a background task that periodically writes to the PriceCache.
        Must seed the cache with initial prices before returning, so SSE
        clients have data immediately.
        """

    @abstractmethod
    async def stop(self) -> None:
        """Stop the background task and release resources.

        Safe to call multiple times.
        """

    @abstractmethod
    async def add_ticker(self, ticker: str) -> None:
        """Add a ticker to the active set. No-op if already present."""

    @abstractmethod
    async def remove_ticker(self, ticker: str) -> None:
        """Remove a ticker from the active set and from the PriceCache."""

    @abstractmethod
    def get_tickers(self) -> list[str]:
        """Return the current list of actively tracked tickers."""
```

**Key contract requirements:**

1. `start()` must seed the cache before returning — SSE clients connect immediately and need data.
2. `stop()` must be idempotent — the FastAPI shutdown handler may call it multiple times.
3. `add_ticker()` / `remove_ticker()` are called from the watchlist and portfolio APIs when tickers are added/removed.
4. The source writes to the cache on its own schedule — callers don't wait for price updates.

---

## 5. Factory — `app/market/factory.py`

A single function that selects the implementation based on environment variables.

```python
from __future__ import annotations
import logging
import os
from .cache import PriceCache
from .interface import MarketDataSource
from .massive_client import MassiveDataSource
from .simulator import SimulatorDataSource

logger = logging.getLogger(__name__)


def create_market_data_source(price_cache: PriceCache) -> MarketDataSource:
    """Create the appropriate market data source based on environment variables.

    - MASSIVE_API_KEY set and non-empty → MassiveDataSource (real market data)
    - Otherwise → SimulatorDataSource (GBM simulation)

    Returns an unstarted source. Caller must await source.start(tickers).
    """
    api_key = os.environ.get("MASSIVE_API_KEY", "").strip()

    if api_key:
        logger.info("Market data source: Massive API (real data)")
        return MassiveDataSource(api_key=api_key, price_cache=price_cache)
    else:
        logger.info("Market data source: GBM Simulator")
        return SimulatorDataSource(price_cache=price_cache)
```

**Why a factory and not dependency injection?**

- The selection is purely environment-driven — no runtime logic needed.
- A single function keeps the startup code clean: `source = create_market_data_source(cache)`.
- Tests can bypass the factory and instantiate either implementation directly.

---

## 6. Simulator Implementation

### 6.1 Seed Data — `app/market/seed_prices.py`

All configuration for the simulator lives in one module: starting prices, per-ticker GBM parameters, and correlation structure.

```python
# Realistic starting prices for the default watchlist
SEED_PRICES: dict[str, float] = {
    "AAPL": 190.00,
    "GOOGL": 175.00,
    "MSFT": 420.00,
    "AMZN": 185.00,
    "TSLA": 250.00,
    "NVDA": 800.00,
    "META": 500.00,
    "JPM": 195.00,
    "V": 280.00,
    "NFLX": 600.00,
}

# Per-ticker GBM parameters
# sigma: annualized volatility (higher = more price movement)
# mu: annualized drift / expected return
TICKER_PARAMS: dict[str, dict[str, float]] = {
    "AAPL": {"sigma": 0.22, "mu": 0.05},
    "GOOGL": {"sigma": 0.25, "mu": 0.05},
    "MSFT": {"sigma": 0.20, "mu": 0.05},
    "AMZN": {"sigma": 0.28, "mu": 0.05},
    "TSLA": {"sigma": 0.50, "mu": 0.03},   # High volatility
    "NVDA": {"sigma": 0.40, "mu": 0.08},   # High volatility, strong drift
    "META": {"sigma": 0.30, "mu": 0.05},
    "JPM": {"sigma": 0.18, "mu": 0.04},    # Low volatility (bank)
    "V": {"sigma": 0.17, "mu": 0.04},      # Low volatility (payments)
    "NFLX": {"sigma": 0.35, "mu": 0.05},
}

# Default parameters for dynamically added tickers
DEFAULT_PARAMS: dict[str, float] = {"sigma": 0.25, "mu": 0.05}

# Correlation groups for Cholesky decomposition
CORRELATION_GROUPS: dict[str, set[str]] = {
    "tech": {"AAPL", "GOOGL", "MSFT", "AMZN", "META", "NVDA", "NFLX"},
    "finance": {"JPM", "V"},
}

# Correlation coefficients
INTRA_TECH_CORR = 0.6     # Tech stocks move together
INTRA_FINANCE_CORR = 0.5  # Finance stocks move together
CROSS_GROUP_CORR = 0.3    # Between sectors / unknown tickers
TSLA_CORR = 0.3           # TSLA does its own thing
```

**Dynamically added tickers** (e.g., user adds "DIS" via watchlist) get:
- A random starting price between $50–$300
- Default sigma=0.25, mu=0.05
- Cross-group correlation (0.3) with all other tickers

### 6.2 GBMSimulator — `app/market/simulator.py`

The core math engine. This is a pure computation class with no async, no cache awareness, and no I/O.

```python
import math
import random
import numpy as np
from .seed_prices import (
    SEED_PRICES, TICKER_PARAMS, DEFAULT_PARAMS,
    CORRELATION_GROUPS, INTRA_TECH_CORR, INTRA_FINANCE_CORR,
    CROSS_GROUP_CORR, TSLA_CORR,
)


class GBMSimulator:
    """Geometric Brownian Motion simulator for correlated stock prices.

    Math:
        S(t+dt) = S(t) * exp((mu - sigma^2/2) * dt + sigma * sqrt(dt) * Z)
    """

    TRADING_SECONDS_PER_YEAR = 252 * 6.5 * 3600  # 5,896,800
    DEFAULT_DT = 0.5 / TRADING_SECONDS_PER_YEAR  # ~8.48e-8

    def __init__(
        self,
        tickers: list[str],
        dt: float = DEFAULT_DT,
        event_probability: float = 0.001,
    ) -> None:
        self._dt = dt
        self._event_prob = event_probability
        self._tickers: list[str] = []
        self._prices: dict[str, float] = {}
        self._params: dict[str, dict[str, float]] = {}
        self._cholesky: np.ndarray | None = None

        for ticker in tickers:
            self._add_ticker_internal(ticker)
        self._rebuild_cholesky()

    def step(self) -> dict[str, float]:
        """Advance all tickers by one time step. Returns {ticker: new_price}."""
        n = len(self._tickers)
        if n == 0:
            return {}

        # Generate n independent standard normal draws
        z_independent = np.random.standard_normal(n)

        # Apply Cholesky to get correlated draws
        if self._cholesky is not None:
            z_correlated = self._cholesky @ z_independent
        else:
            z_correlated = z_independent

        result: dict[str, float] = {}
        for i, ticker in enumerate(self._tickers):
            params = self._params[ticker]
            mu = params["mu"]
            sigma = params["sigma"]

            # GBM formula
            drift = (mu - 0.5 * sigma**2) * self._dt
            diffusion = sigma * math.sqrt(self._dt) * z_correlated[i]
            self._prices[ticker] *= math.exp(drift + diffusion)

            # Random event: ~0.1% chance per tick per ticker
            if random.random() < self._event_prob:
                shock = random.uniform(0.02, 0.05) * random.choice([-1, 1])
                self._prices[ticker] *= 1 + shock

            result[ticker] = round(self._prices[ticker], 2)

        return result

    def add_ticker(self, ticker: str) -> None:
        if ticker in self._prices:
            return
        self._add_ticker_internal(ticker)
        self._rebuild_cholesky()

    def remove_ticker(self, ticker: str) -> None:
        if ticker not in self._prices:
            return
        self._tickers.remove(ticker)
        del self._prices[ticker]
        del self._params[ticker]
        self._rebuild_cholesky()

    def get_price(self, ticker: str) -> float | None:
        return self._prices.get(ticker)

    def get_tickers(self) -> list[str]:
        return list(self._tickers)

    # --- Internals ---

    def _add_ticker_internal(self, ticker: str) -> None:
        if ticker in self._prices:
            return
        self._tickers.append(ticker)
        self._prices[ticker] = SEED_PRICES.get(ticker, random.uniform(50.0, 300.0))
        self._params[ticker] = TICKER_PARAMS.get(ticker, dict(DEFAULT_PARAMS))

    def _rebuild_cholesky(self) -> None:
        """Rebuild the Cholesky decomposition of the correlation matrix."""
        n = len(self._tickers)
        if n <= 1:
            self._cholesky = None
            return

        corr = np.eye(n)
        for i in range(n):
            for j in range(i + 1, n):
                rho = self._pairwise_correlation(self._tickers[i], self._tickers[j])
                corr[i, j] = rho
                corr[j, i] = rho

        self._cholesky = np.linalg.cholesky(corr)

    @staticmethod
    def _pairwise_correlation(t1: str, t2: str) -> float:
        tech = CORRELATION_GROUPS["tech"]
        finance = CORRELATION_GROUPS["finance"]

        if t1 == "TSLA" or t2 == "TSLA":
            return TSLA_CORR
        if t1 in tech and t2 in tech:
            return INTRA_TECH_CORR
        if t1 in finance and t2 in finance:
            return INTRA_FINANCE_CORR
        return CROSS_GROUP_CORR
```

**Why Cholesky decomposition?**

In real markets, stocks are correlated — AAPL and MSFT tend to move in the same direction. To simulate this:

1. Define an N×N correlation matrix `C` where `C[i,j]` is the desired correlation between tickers i and j.
2. Compute the lower-triangular matrix `L` such that `L @ L^T = C` (Cholesky decomposition).
3. Each tick, generate N independent standard normal draws `Z_indep`.
4. Multiply: `Z_corr = L @ Z_indep` — the resulting vector has the desired correlation structure.

This is a standard technique in quantitative finance (Monte Carlo simulation). The matrix is rebuilt only when tickers are added/removed, which is rare. The per-tick cost is one matrix-vector multiply (O(n²) for n tickers, negligible for n < 50).

**Random events:**

Each tick, each ticker has a 0.1% chance of a price shock (2–5%, randomly up or down). With 10 tickers ticking twice per second, expect an event roughly every 50 seconds. This creates the visual drama of sudden price movements that makes the demo engaging.

### 6.3 SimulatorDataSource — `app/market/simulator.py`

Wraps `GBMSimulator` in an async background task that writes to the PriceCache.

```python
import asyncio
import logging
from .cache import PriceCache
from .interface import MarketDataSource

logger = logging.getLogger(__name__)


class SimulatorDataSource(MarketDataSource):
    """MarketDataSource backed by the GBM simulator."""

    def __init__(
        self,
        price_cache: PriceCache,
        update_interval: float = 0.5,
        event_probability: float = 0.001,
    ) -> None:
        self._cache = price_cache
        self._interval = update_interval
        self._event_prob = event_probability
        self._sim: GBMSimulator | None = None
        self._task: asyncio.Task | None = None

    async def start(self, tickers: list[str]) -> None:
        self._sim = GBMSimulator(
            tickers=tickers,
            event_probability=self._event_prob,
        )
        # Seed the cache immediately so SSE clients have data on connect
        for ticker in tickers:
            price = self._sim.get_price(ticker)
            if price is not None:
                self._cache.update(ticker=ticker, price=price)

        self._task = asyncio.create_task(self._run_loop(), name="simulator-loop")
        logger.info("Simulator started with %d tickers", len(tickers))

    async def stop(self) -> None:
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self._task = None
        logger.info("Simulator stopped")

    async def add_ticker(self, ticker: str) -> None:
        if self._sim:
            self._sim.add_ticker(ticker)
            price = self._sim.get_price(ticker)
            if price is not None:
                self._cache.update(ticker=ticker, price=price)
            logger.info("Simulator: added ticker %s", ticker)

    async def remove_ticker(self, ticker: str) -> None:
        if self._sim:
            self._sim.remove_ticker(ticker)
        self._cache.remove(ticker)
        logger.info("Simulator: removed ticker %s", ticker)

    def get_tickers(self) -> list[str]:
        return self._sim.get_tickers() if self._sim else []

    async def _run_loop(self) -> None:
        """Core loop: step the simulation, write to cache, sleep."""
        while True:
            try:
                if self._sim:
                    prices = self._sim.step()
                    for ticker, price in prices.items():
                        self._cache.update(ticker=ticker, price=price)
            except Exception:
                logger.exception("Simulator step failed")
            await asyncio.sleep(self._interval)
```

**Background task lifecycle:**

```
start() called
  │
  ├─ Create GBMSimulator with initial tickers
  ├─ Seed PriceCache with initial prices (synchronous)
  └─ Spawn asyncio.Task running _run_loop()
       │
       └─ Loop forever:
            ├─ sim.step() → {ticker: price}
            ├─ cache.update(ticker, price) for each
            └─ asyncio.sleep(0.5)

stop() called
  │
  ├─ task.cancel()
  └─ await task (catches CancelledError)
```

---

## 7. Massive API Implementation — `app/market/massive_client.py`

### 7.1 API Details

**Endpoint:** `GET /v2/snapshot/locale/us/markets/stocks/tickers?tickers=AAPL,GOOGL,...`

This single call returns the latest trade price for all requested tickers. It's the most efficient approach — one HTTP request regardless of how many tickers we track.

**Response fields used:**
- `snap.ticker` — ticker symbol
- `snap.last_trade.price` — latest trade price (float)
- `snap.last_trade.timestamp` — Unix milliseconds (int)

**Rate limit strategy:**
- Free tier: 5 requests/minute → poll every 15 seconds (4 req/min, safe margin)
- The `poll_interval` parameter can be lowered for paid tiers

### 7.2 MassiveDataSource Implementation

```python
import asyncio
import logging
from massive import RESTClient
from massive.rest.models import SnapshotMarketType
from .cache import PriceCache
from .interface import MarketDataSource

logger = logging.getLogger(__name__)


class MassiveDataSource(MarketDataSource):
    """MarketDataSource backed by the Massive (Polygon.io) REST API."""

    def __init__(
        self,
        api_key: str,
        price_cache: PriceCache,
        poll_interval: float = 15.0,
    ) -> None:
        self._api_key = api_key
        self._cache = price_cache
        self._interval = poll_interval
        self._tickers: list[str] = []
        self._task: asyncio.Task | None = None
        self._client: RESTClient | None = None

    async def start(self, tickers: list[str]) -> None:
        self._client = RESTClient(api_key=self._api_key)
        self._tickers = list(tickers)

        # Immediate first poll so the cache has data right away
        await self._poll_once()

        self._task = asyncio.create_task(self._poll_loop(), name="massive-poller")
        logger.info(
            "Massive poller started: %d tickers, %.1fs interval",
            len(tickers), self._interval,
        )

    async def stop(self) -> None:
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self._task = None
        self._client = None
        logger.info("Massive poller stopped")

    async def add_ticker(self, ticker: str) -> None:
        ticker = ticker.upper().strip()
        if ticker not in self._tickers:
            self._tickers.append(ticker)
            logger.info("Massive: added ticker %s (will appear on next poll)", ticker)

    async def remove_ticker(self, ticker: str) -> None:
        ticker = ticker.upper().strip()
        self._tickers = [t for t in self._tickers if t != ticker]
        self._cache.remove(ticker)
        logger.info("Massive: removed ticker %s", ticker)

    def get_tickers(self) -> list[str]:
        return list(self._tickers)

    async def _poll_loop(self) -> None:
        """Poll on interval. First poll already happened in start()."""
        while True:
            await asyncio.sleep(self._interval)
            await self._poll_once()

    async def _poll_once(self) -> None:
        """Execute one poll cycle: fetch snapshots, update cache."""
        if not self._tickers or not self._client:
            return

        try:
            # The Massive RESTClient is synchronous — run in a thread
            # to avoid blocking the event loop.
            snapshots = await asyncio.to_thread(self._fetch_snapshots)
            processed = 0
            for snap in snapshots:
                try:
                    price = snap.last_trade.price
                    # Massive timestamps are Unix milliseconds → convert to seconds
                    timestamp = snap.last_trade.timestamp / 1000.0
                    self._cache.update(
                        ticker=snap.ticker,
                        price=price,
                        timestamp=timestamp,
                    )
                    processed += 1
                except (AttributeError, TypeError) as e:
                    logger.warning(
                        "Skipping snapshot for %s: %s",
                        getattr(snap, "ticker", "???"), e,
                    )
            logger.debug("Massive poll: updated %d/%d tickers", processed, len(self._tickers))

        except Exception as e:
            logger.error("Massive poll failed: %s", e)
            # Don't re-raise — the loop retries on the next interval.
            # Common failures: 401 (bad key), 429 (rate limit), network errors.

    def _fetch_snapshots(self) -> list:
        """Synchronous call to the Massive REST API. Runs in a thread."""
        return self._client.get_snapshot_all(
            market_type=SnapshotMarketType.STOCKS,
            tickers=self._tickers,
        )
```

**Why `asyncio.to_thread()`?**

The `massive` Python client (`RESTClient`) uses synchronous HTTP (it's built on `requests` or `urllib3`). Calling it directly in an async context would block the event loop for the duration of the HTTP request (typically 100–500ms). By running it in a thread via `asyncio.to_thread()`, the event loop stays responsive for SSE connections and other API requests.

**Error handling strategy:**

The `_poll_once` method uses a broad `except Exception` that logs and continues. This is intentional:

| Error | Behavior |
|-------|----------|
| 401 Unauthorized | Logged once per poll. User must fix their API key. |
| 429 Rate Limited | Logged. Next poll retries after `poll_interval`. |
| Network error | Logged. Next poll retries. Transient errors self-heal. |
| Malformed snapshot | Individual ticker skipped, others still processed. |

There is no exponential backoff or circuit breaker because:
- The poll interval (15s) is already a natural cooldown
- The free tier allows 5 req/min; we use 4 req/min
- Network errors are typically transient and resolve within one interval

**Ticker normalization:**

`add_ticker()` and `remove_ticker()` normalize input to uppercase and strip whitespace. This prevents duplicates from inconsistent casing (e.g., "aapl" vs "AAPL"). The simulator doesn't need this because its seed data is already uppercase, but Massive does because tickers may come from user input.

---

## 8. SSE Streaming — `app/market/stream.py`

### 8.1 Endpoint Design

```
GET /api/stream/prices
Content-Type: text/event-stream
Cache-Control: no-cache
Connection: keep-alive
```

The SSE endpoint pushes all tracked prices to connected clients every ~500ms. It uses the standard `text/event-stream` format compatible with the browser's `EventSource` API.

### 8.2 Implementation

```python
import asyncio
import json
import logging
from collections.abc import AsyncGenerator
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from .cache import PriceCache

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/stream", tags=["streaming"])


def create_stream_router(price_cache: PriceCache) -> APIRouter:
    """Create the SSE streaming router with a reference to the price cache."""

    @router.get("/prices")
    async def stream_prices(request: Request) -> StreamingResponse:
        return StreamingResponse(
            _generate_events(price_cache, request),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",  # Disable nginx buffering
            },
        )

    return router


async def _generate_events(
    price_cache: PriceCache,
    request: Request,
    interval: float = 0.5,
) -> AsyncGenerator[str, None]:
    """Async generator yielding SSE-formatted price events."""
    # Tell the client to retry after 1 second on disconnect
    yield "retry: 1000\n\n"

    last_version = -1
    client_ip = request.client.host if request.client else "unknown"
    logger.info("SSE client connected: %s", client_ip)

    try:
        while True:
            if await request.is_disconnected():
                logger.info("SSE client disconnected: %s", client_ip)
                break

            current_version = price_cache.version
            if current_version != last_version:
                last_version = current_version
                prices = price_cache.get_all()

                if prices:
                    data = {
                        ticker: update.to_dict()
                        for ticker, update in prices.items()
                    }
                    payload = json.dumps(data)
                    yield f"data: {payload}\n\n"

            await asyncio.sleep(interval)
    except asyncio.CancelledError:
        logger.info("SSE stream cancelled for: %s", client_ip)
```

### 8.3 SSE Protocol Details

**Wire format:**

```
retry: 1000\n\n
data: {"AAPL": {"ticker": "AAPL", "price": 191.23, ...}, "GOOGL": {...}}\n\n
data: {"AAPL": {"ticker": "AAPL", "price": 191.25, ...}, "GOOGL": {...}}\n\n
```

- Each event is a `data:` line followed by two newlines
- The `retry: 1000` directive tells the browser to reconnect after 1 second if the connection drops
- The entire payload is a JSON object keyed by ticker symbol

**Change detection with `version`:**

The generator tracks the last-seen `PriceCache.version`. On each iteration:
1. Read `price_cache.version` (cheap, no lock needed for reading an int)
2. If unchanged → skip (no new data to send)
3. If changed → read all prices, serialize, and yield

This avoids unnecessary JSON serialization when nothing has changed. In practice, with the simulator running at 500ms intervals, every other check will find new data.

**Client reconnection:**

The browser's `EventSource` API handles reconnection automatically:
1. Connection drops (network error, server restart)
2. Browser waits 1 second (`retry: 1000`)
3. Browser sends a new `GET /api/stream/prices` request
4. Server starts a fresh event stream
5. Client receives all current prices immediately (first event after version check)

No state synchronization is needed because each event contains the full price snapshot.

### 8.4 Frontend Client Usage

```typescript
const eventSource = new EventSource('/api/stream/prices');

eventSource.onmessage = (event) => {
  const prices: Record<string, PriceUpdate> = JSON.parse(event.data);

  for (const [ticker, update] of Object.entries(prices)) {
    // update.price, update.previous_price, update.direction, etc.
    updateTickerDisplay(ticker, update);
  }
};

eventSource.onerror = () => {
  // EventSource auto-reconnects; update connection status indicator
  setConnectionStatus('reconnecting');
};
```

---

## 9. FastAPI Application Integration

### 9.1 Lifespan Handler

The market data source is started and stopped via FastAPI's lifespan context manager. This ensures clean startup/shutdown and makes the cache and source available to all routes.

```python
# backend/app/main.py (relevant excerpts)
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.market import PriceCache, create_market_data_source, create_stream_router

# These will be set during lifespan and accessed by route handlers
price_cache: PriceCache | None = None
market_source: MarketDataSource | None = None

DEFAULT_TICKERS = ["AAPL", "GOOGL", "MSFT", "AMZN", "TSLA",
                    "NVDA", "META", "JPM", "V", "NFLX"]


@asynccontextmanager
async def lifespan(app: FastAPI):
    global price_cache, market_source

    # --- Startup ---
    price_cache = PriceCache()
    market_source = create_market_data_source(price_cache)

    # Load tickers from DB (watchlist + held positions)
    # For initial startup with empty DB, use defaults
    tickers = load_tracked_tickers_from_db() or DEFAULT_TICKERS
    await market_source.start(tickers)

    yield  # App runs here

    # --- Shutdown ---
    await market_source.stop()


app = FastAPI(title="FinAlly", lifespan=lifespan)

# Mount the SSE streaming router
# Note: create_stream_router is called after lifespan sets up price_cache
# In practice, the router is created eagerly and reads from the cache reference
stream_router = create_stream_router(price_cache)
app.include_router(stream_router)
```

### 9.2 Ticker Tracking: Watchlist + Positions

The market data source tracks the **union** of watchlist tickers and held-position tickers. This ensures portfolio P&L stays live even if a held ticker is removed from the watchlist.

```python
# When a ticker is added to the watchlist
async def add_to_watchlist(ticker: str):
    db.add_watchlist_entry(ticker)
    await market_source.add_ticker(ticker)  # Start tracking prices

# When a ticker is removed from the watchlist
async def remove_from_watchlist(ticker: str):
    db.remove_watchlist_entry(ticker)
    # Only stop tracking if the ticker is NOT held in a position
    if not db.has_position(ticker):
        await market_source.remove_ticker(ticker)

# When a position is fully closed (sold all shares)
async def on_position_closed(ticker: str):
    # Only stop tracking if the ticker is NOT on the watchlist
    if not db.is_on_watchlist(ticker):
        await market_source.remove_ticker(ticker)
```

This logic prevents a scenario where:
1. User buys AAPL (position exists)
2. User removes AAPL from watchlist
3. Without the union check, AAPL would stop receiving price updates
4. Portfolio P&L for AAPL would freeze at the last known price

### 9.3 How Other Endpoints Use the Cache

**Portfolio valuation (`GET /api/portfolio`):**

```python
@router.get("/api/portfolio")
async def get_portfolio():
    positions = db.get_positions()
    total_value = user.cash_balance

    position_data = []
    for pos in positions:
        current_price = price_cache.get_price(pos.ticker)
        if current_price is None:
            current_price = pos.avg_cost  # Fallback if no price yet

        market_value = current_price * pos.quantity
        unrealized_pnl = (current_price - pos.avg_cost) * pos.quantity
        total_value += market_value

        position_data.append({
            "ticker": pos.ticker,
            "quantity": pos.quantity,
            "avg_cost": pos.avg_cost,
            "current_price": current_price,
            "market_value": market_value,
            "unrealized_pnl": unrealized_pnl,
            "pnl_percent": (current_price - pos.avg_cost) / pos.avg_cost * 100,
        })

    return {
        "cash_balance": user.cash_balance,
        "positions": position_data,
        "total_value": total_value,
    }
```

**Trade execution (`POST /api/portfolio/trade`):**

```python
@router.post("/api/portfolio/trade")
async def execute_trade(request: TradeRequest):
    current_price = price_cache.get_price(request.ticker)
    if current_price is None:
        raise HTTPException(400, f"No price available for {request.ticker}")

    if request.side == "buy":
        cost = current_price * request.quantity
        if cost > user.cash_balance:
            raise HTTPException(400,
                f"Insufficient cash: need ${cost:.2f} but only "
                f"${user.cash_balance:.2f} available"
            )
        # Execute buy...
    elif request.side == "sell":
        position = db.get_position(request.ticker)
        if not position or position.quantity < request.quantity:
            raise HTTPException(400, "Insufficient shares")
        # Execute sell...
```

---

## 10. Testing Strategy

### 10.1 Unit Tests for PriceUpdate

```python
# tests/market/test_models.py

def test_price_update_direction_up():
    update = PriceUpdate(ticker="AAPL", price=191.0, previous_price=190.0)
    assert update.direction == "up"
    assert update.change == 1.0
    assert update.change_percent > 0

def test_price_update_direction_down():
    update = PriceUpdate(ticker="AAPL", price=189.0, previous_price=190.0)
    assert update.direction == "down"

def test_price_update_flat():
    update = PriceUpdate(ticker="AAPL", price=190.0, previous_price=190.0)
    assert update.direction == "flat"
    assert update.change == 0.0

def test_price_update_to_dict():
    update = PriceUpdate(ticker="AAPL", price=191.0, previous_price=190.0, timestamp=1000.0)
    d = update.to_dict()
    assert d["ticker"] == "AAPL"
    assert d["price"] == 191.0
    assert d["direction"] == "up"
    assert "change" in d
    assert "change_percent" in d

def test_price_update_zero_previous():
    """Division by zero guard."""
    update = PriceUpdate(ticker="X", price=10.0, previous_price=0.0)
    assert update.change_percent == 0.0
```

### 10.2 Unit Tests for PriceCache

```python
# tests/market/test_cache.py

def test_cache_first_update_is_flat():
    cache = PriceCache()
    update = cache.update("AAPL", 190.0)
    assert update.direction == "flat"
    assert update.previous_price == 190.0

def test_cache_second_update_has_direction():
    cache = PriceCache()
    cache.update("AAPL", 190.0)
    update = cache.update("AAPL", 191.0)
    assert update.direction == "up"
    assert update.previous_price == 190.0

def test_cache_version_increments():
    cache = PriceCache()
    assert cache.version == 0
    cache.update("AAPL", 190.0)
    assert cache.version == 1
    cache.update("AAPL", 191.0)
    assert cache.version == 2

def test_cache_get_all_returns_copy():
    cache = PriceCache()
    cache.update("AAPL", 190.0)
    all_prices = cache.get_all()
    all_prices["FAKE"] = None  # Mutating the copy
    assert "FAKE" not in cache  # Original unaffected

def test_cache_remove():
    cache = PriceCache()
    cache.update("AAPL", 190.0)
    cache.remove("AAPL")
    assert cache.get("AAPL") is None

def test_cache_rounds_prices():
    cache = PriceCache()
    update = cache.update("AAPL", 190.123456)
    assert update.price == 190.12
```

### 10.3 Unit Tests for GBMSimulator

```python
# tests/market/test_simulator.py

def test_simulator_step_returns_all_tickers():
    sim = GBMSimulator(tickers=["AAPL", "GOOGL", "MSFT"])
    prices = sim.step()
    assert set(prices.keys()) == {"AAPL", "GOOGL", "MSFT"}

def test_simulator_prices_are_positive():
    """GBM can never produce negative prices (multiplicative model)."""
    sim = GBMSimulator(tickers=["AAPL"])
    for _ in range(1000):
        prices = sim.step()
        assert prices["AAPL"] > 0

def test_simulator_add_ticker():
    sim = GBMSimulator(tickers=["AAPL"])
    sim.add_ticker("GOOGL")
    assert "GOOGL" in sim.get_tickers()
    prices = sim.step()
    assert "GOOGL" in prices

def test_simulator_remove_ticker():
    sim = GBMSimulator(tickers=["AAPL", "GOOGL"])
    sim.remove_ticker("GOOGL")
    assert "GOOGL" not in sim.get_tickers()
    prices = sim.step()
    assert "GOOGL" not in prices

def test_simulator_add_unknown_ticker():
    """Unknown tickers get random prices and default params."""
    sim = GBMSimulator(tickers=["AAPL"])
    sim.add_ticker("XYZ")
    price = sim.get_price("XYZ")
    assert price is not None
    assert 50.0 <= price <= 300.0

def test_simulator_empty():
    sim = GBMSimulator(tickers=[])
    assert sim.step() == {}
```

### 10.4 Integration Tests for SimulatorDataSource

```python
# tests/market/test_simulator_source.py
import asyncio

async def test_simulator_source_seeds_cache():
    cache = PriceCache()
    source = SimulatorDataSource(price_cache=cache)
    await source.start(["AAPL", "GOOGL"])

    # Cache should have data immediately after start()
    assert cache.get("AAPL") is not None
    assert cache.get("GOOGL") is not None

    await source.stop()

async def test_simulator_source_updates_cache():
    cache = PriceCache()
    source = SimulatorDataSource(price_cache=cache, update_interval=0.1)
    await source.start(["AAPL"])

    initial_version = cache.version
    await asyncio.sleep(0.3)  # Allow 2-3 update cycles

    assert cache.version > initial_version
    await source.stop()

async def test_simulator_source_stop_is_idempotent():
    cache = PriceCache()
    source = SimulatorDataSource(price_cache=cache)
    await source.start(["AAPL"])
    await source.stop()
    await source.stop()  # Should not raise
```

### 10.5 Unit Tests for Factory

```python
# tests/market/test_factory.py
import os

def test_factory_returns_simulator_by_default(monkeypatch):
    monkeypatch.delenv("MASSIVE_API_KEY", raising=False)
    cache = PriceCache()
    source = create_market_data_source(cache)
    assert isinstance(source, SimulatorDataSource)

def test_factory_returns_massive_with_key(monkeypatch):
    monkeypatch.setenv("MASSIVE_API_KEY", "test-key-123")
    cache = PriceCache()
    source = create_market_data_source(cache)
    assert isinstance(source, MassiveDataSource)

def test_factory_ignores_empty_key(monkeypatch):
    monkeypatch.setenv("MASSIVE_API_KEY", "   ")
    cache = PriceCache()
    source = create_market_data_source(cache)
    assert isinstance(source, SimulatorDataSource)
```

---

## 11. Data Flow Diagrams

### 11.1 Simulator Mode (Default)

```
                    Every 500ms
                    ┌──────────────────────────────┐
                    │                              │
                    ▼                              │
┌────────────────────────┐     ┌──────────────┐    │
│ GBMSimulator.step()    │────▶│ PriceCache   │    │
│                        │     │   .update()   │    │
│ For each ticker:       │     └──────┬───────┘    │
│   1. Generate Z_corr   │            │            │
│   2. Apply GBM formula │            │         asyncio.sleep(0.5)
│   3. Check for events  │            │            │
│   4. Round to 2dp      │            ▼            │
└────────────────────────┘     version incremented─┘

                                       │
                    ┌──────────────────┼──────────────────┐
                    │                  │                  │
                    ▼                  ▼                  ▼
            SSE Generator       Portfolio API       Trade API
            checks version →    cache.get_price()   cache.get_price()
            sends if changed
```

### 11.2 Massive Mode

```
                    Every 15s
                    ┌──────────────────────────────┐
                    │                              │
                    ▼                              │
┌────────────────────────┐                         │
│ asyncio.to_thread(     │                         │
│   client.get_snapshot_ │                         │
│   all(tickers)         │                         │
│ )                      │                         │
└────────┬───────────────┘                         │
         │                                    asyncio.sleep(15)
         ▼                                         │
┌────────────────────────┐     ┌──────────────┐    │
│ For each snapshot:     │────▶│ PriceCache   │    │
│   price = last_trade.p │     │   .update()   │────┘
│   ts = last_trade.t    │     └──────────────┘
│        / 1000.0        │
└────────────────────────┘
```

### 11.3 SSE Event Flow (Client Perspective)

```
Browser                          Server
  │                                │
  ├──GET /api/stream/prices───────▶│
  │                                ├── yield "retry: 1000\n\n"
  │◀─── retry: 1000 ──────────────┤
  │                                │
  │                                ├── check version (changed?)
  │                                ├── yes → serialize all prices
  │◀─── data: {...} ──────────────┤
  │                                ├── sleep 0.5s
  │                                │
  │                                ├── check version (unchanged?)
  │                                ├── no → skip
  │                                ├── sleep 0.5s
  │                                │
  │                                ├── check version (changed?)
  │◀─── data: {...} ──────────────┤
  │                                ├── sleep 0.5s
  │                                │
  ├── (connection drops) ─────────│
  │                                │
  │  ... 1 second (retry) ...      │
  │                                │
  ├──GET /api/stream/prices───────▶│
  │                                ├── yield "retry: 1000\n\n"
  │◀─── retry: 1000 ──────────────┤
  │◀─── data: {...} ──────────────┤  (full snapshot immediately)
  │                                │
```

---

## 12. Configuration Summary

| Parameter | Default | Source | Description |
|-----------|---------|--------|-------------|
| `MASSIVE_API_KEY` | _(empty)_ | Environment variable | If set, use real market data |
| Simulator update interval | 500ms | `SimulatorDataSource(update_interval=0.5)` | GBM tick rate |
| Simulator event probability | 0.001 | `GBMSimulator(event_probability=0.001)` | Random shock chance per tick per ticker |
| Massive poll interval | 15s | `MassiveDataSource(poll_interval=15.0)` | REST API polling rate |
| SSE push interval | 500ms | `_generate_events(interval=0.5)` | How often the SSE stream checks for new data |
| SSE retry directive | 1000ms | Hardcoded in `_generate_events` | Browser reconnect delay |
| GBM dt | ~8.48e-8 | `GBMSimulator.DEFAULT_DT` | Time step as fraction of trading year |
| Dynamic ticker price range | $50–$300 | `seed_prices.py` / `_add_ticker_internal` | Random price for unknown tickers |

---

## 13. Dependencies

From `pyproject.toml`:

| Package | Version | Purpose |
|---------|---------|---------|
| `fastapi` | ≥0.115.0 | Web framework, SSE streaming |
| `uvicorn[standard]` | ≥0.32.0 | ASGI server |
| `numpy` | ≥2.0.0 | Cholesky decomposition, correlated random draws |
| `massive` | ≥1.0.0 | Polygon.io REST client (for real market data) |
| `rich` | ≥13.0.0 | Terminal demo dashboard |
| `pytest` | ≥8.3.0 | Testing (dev) |
| `pytest-asyncio` | ≥0.24.0 | Async test support (dev) |
