"""Watchlist CRUD logic."""

from datetime import datetime, timezone

from app.db import get_db
from app.market import PriceCache, MarketDataSource


async def get_watchlist(price_cache: PriceCache) -> list[dict]:
    """Return watchlist tickers with latest prices."""
    db = await get_db()
    cursor = await db.execute(
        "SELECT ticker FROM watchlist WHERE user_id = ? ORDER BY ticker",
        ("default",),
    )
    rows = await cursor.fetchall()
    return [
        {"ticker": row[0], "price": price_cache.get_price(row[0])}
        for row in rows
    ]


async def add_ticker(
    ticker: str, price_cache: PriceCache, data_source: MarketDataSource
) -> dict:
    """Add ticker to watchlist and start price tracking."""
    ticker = ticker.upper()
    db = await get_db()
    now = datetime.now(timezone.utc).isoformat()
    await db.execute(
        "INSERT OR IGNORE INTO watchlist (user_id, ticker, added_at) VALUES (?, ?, ?)",
        ("default", ticker, now),
    )
    await db.commit()
    await data_source.add_ticker(ticker)
    return {"ticker": ticker, "price": price_cache.get_price(ticker)}


async def remove_ticker(ticker: str, data_source: MarketDataSource) -> None:
    """Remove ticker from watchlist. Only stop tracking if no position held."""
    ticker = ticker.upper()
    db = await get_db()
    await db.execute(
        "DELETE FROM watchlist WHERE user_id = ? AND ticker = ?",
        ("default", ticker),
    )
    await db.commit()
    cursor = await db.execute(
        "SELECT 1 FROM positions WHERE user_id = ? AND ticker = ?",
        ("default", ticker),
    )
    has_position = await cursor.fetchone()
    if not has_position:
        await data_source.remove_ticker(ticker)
