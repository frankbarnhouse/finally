"""FinAlly backend application."""

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles  # noqa: F401 — used in Phase 4

from app.db import get_db, close_db, DEFAULT_TICKERS
from app.market import PriceCache, create_market_data_source, create_stream_router
from app.api.portfolio import create_portfolio_router
from app.api.watchlist import create_watchlist_router
from app.api.health import create_health_router
from app.services.portfolio import record_snapshot

price_cache = PriceCache()
data_source = create_market_data_source(price_cache)
_snapshot_task: asyncio.Task | None = None


async def snapshot_loop(interval: float = 30.0):
    """Record portfolio value every interval seconds."""
    while True:
        await asyncio.sleep(interval)
        try:
            await record_snapshot(price_cache)
        except Exception:
            pass  # snapshot failure is non-fatal


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _snapshot_task
    await get_db()
    await data_source.start(DEFAULT_TICKERS)
    _snapshot_task = asyncio.create_task(snapshot_loop())
    yield
    if _snapshot_task:
        _snapshot_task.cancel()
        try:
            await _snapshot_task
        except asyncio.CancelledError:
            pass
    await data_source.stop()
    await close_db()


app = FastAPI(title="FinAlly", lifespan=lifespan)

app.include_router(create_stream_router(price_cache))
app.include_router(create_portfolio_router(price_cache))
app.include_router(create_watchlist_router(price_cache, data_source))
app.include_router(create_health_router())
