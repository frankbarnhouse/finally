"""Watchlist REST endpoints."""

from fastapi import APIRouter
from pydantic import BaseModel

from app.market import PriceCache, MarketDataSource
from app.services.watchlist import get_watchlist, add_ticker, remove_ticker


class AddTickerRequest(BaseModel):
    ticker: str


def create_watchlist_router(
    price_cache: PriceCache, data_source: MarketDataSource
) -> APIRouter:
    """Create the watchlist router with injected dependencies."""
    router = APIRouter(prefix="/api/watchlist", tags=["watchlist"])

    @router.get("")
    async def get_watchlist_endpoint():
        return await get_watchlist(price_cache)

    @router.post("")
    async def add_ticker_endpoint(req: AddTickerRequest):
        return await add_ticker(req.ticker, price_cache, data_source)

    @router.delete("/{ticker}")
    async def remove_ticker_endpoint(ticker: str):
        await remove_ticker(ticker, data_source)
        return {"status": "ok"}

    return router
