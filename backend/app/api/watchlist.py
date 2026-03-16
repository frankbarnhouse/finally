"""Watchlist API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.db import get_db, get_watchlist, add_to_watchlist, remove_from_watchlist, get_position
from app.market import PriceCache, MarketDataSource

router = APIRouter(prefix="/api", tags=["watchlist"])

_price_cache: PriceCache | None = None
_market_source: MarketDataSource | None = None


def init_watchlist_router(price_cache: PriceCache, market_source: MarketDataSource) -> None:
    """Inject shared dependencies into the watchlist router."""
    global _price_cache, _market_source
    _price_cache = price_cache
    _market_source = market_source


class AddTickerRequest(BaseModel):
    ticker: str


@router.get("/watchlist")
async def list_watchlist() -> list[dict]:
    """Return current watchlist tickers with latest prices."""
    db = await get_db()
    items = await get_watchlist(db)
    result = []
    for item in items:
        ticker = item["ticker"]
        price_update = _price_cache.get(ticker) if _price_cache else None
        entry = {"ticker": ticker, "added_at": item["added_at"]}
        if price_update:
            entry.update(price_update.to_dict())
        result.append(entry)
    return result


@router.post("/watchlist", status_code=201)
async def add_ticker(body: AddTickerRequest) -> dict:
    """Add a ticker to the watchlist."""
    ticker = body.ticker.upper()
    db = await get_db()
    item = await add_to_watchlist(db, ticker)
    if _market_source:
        await _market_source.add_ticker(ticker)
    return item


@router.delete("/watchlist/{ticker}")
async def remove_ticker(ticker: str) -> dict:
    """Remove a ticker from the watchlist.

    If the ticker is held in positions, it stays in the market data source
    so prices keep updating for portfolio valuation.
    """
    ticker = ticker.upper()
    db = await get_db()
    removed = await remove_from_watchlist(db, ticker)
    if not removed:
        raise HTTPException(status_code=404, detail=f"Ticker {ticker} not on watchlist")
    # Only remove from market data if not held in a position
    position = await get_position(db, ticker)
    if not position and _market_source:
        await _market_source.remove_ticker(ticker)
    return {"removed": ticker}
