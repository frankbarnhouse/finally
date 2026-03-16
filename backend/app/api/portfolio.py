"""Portfolio API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.db import (
    get_db,
    get_user_profile,
    get_positions,
    insert_snapshot,
    get_snapshots,
)
from app.market import PriceCache
from app.trade import execute_trade as _execute_trade

router = APIRouter(prefix="/api", tags=["portfolio"])

_price_cache: PriceCache | None = None


def init_portfolio_router(price_cache: PriceCache) -> None:
    """Inject the price cache dependency."""
    global _price_cache
    _price_cache = price_cache


class TradeRequest(BaseModel):
    ticker: str
    quantity: float
    side: str  # "buy" or "sell"


@router.get("/portfolio")
async def get_portfolio() -> dict:
    """Return positions, cash balance, total value, and unrealized P&L."""
    db = await get_db()
    profile = await get_user_profile(db)
    cash = profile["cash_balance"]
    positions = await get_positions(db)

    enriched = []
    positions_value = 0.0
    for pos in positions:
        ticker = pos["ticker"]
        current_price = _price_cache.get_price(ticker) if _price_cache else None
        entry = {
            "ticker": ticker,
            "quantity": pos["quantity"],
            "avg_cost": pos["avg_cost"],
            "current_price": current_price,
            "unrealized_pnl": None,
            "pnl_percent": None,
        }
        if current_price is not None:
            market_value = current_price * pos["quantity"]
            cost_basis = pos["avg_cost"] * pos["quantity"]
            entry["unrealized_pnl"] = round(market_value - cost_basis, 2)
            entry["pnl_percent"] = (
                round((market_value - cost_basis) / cost_basis * 100, 2) if cost_basis else 0.0
            )
            positions_value += market_value
        enriched.append(entry)

    total_value = round(cash + positions_value, 2)
    total_pnl = sum(p["unrealized_pnl"] for p in enriched if p["unrealized_pnl"] is not None)

    return {
        "cash_balance": cash,
        "positions": enriched,
        "total_value": total_value,
        "unrealized_pnl": round(total_pnl, 2),
    }


@router.post("/portfolio/trade")
async def trade_endpoint(body: TradeRequest) -> dict:
    """Execute a market order (buy or sell)."""
    db = await get_db()
    try:
        result = await _execute_trade(db, body.ticker, body.side, body.quantity, _price_cache)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Record portfolio snapshot after trade
    await _record_snapshot(db)
    return result


@router.get("/portfolio/history")
async def portfolio_history() -> list[dict]:
    """Return portfolio value snapshots over time."""
    db = await get_db()
    return await get_snapshots(db)


async def _record_snapshot(db=None) -> None:
    """Record a portfolio snapshot (called after trades and by background task)."""
    if db is None:
        db = await get_db()
    profile = await get_user_profile(db)
    cash = profile["cash_balance"]
    positions = await get_positions(db)
    positions_value = 0.0
    for pos in positions:
        price = _price_cache.get_price(pos["ticker"]) if _price_cache else None
        if price is not None:
            positions_value += price * pos["quantity"]
    total_value = round(cash + positions_value, 2)
    await insert_snapshot(db, total_value)


async def record_snapshot_task() -> None:
    """Public entry point for the background snapshot task."""
    await _record_snapshot()
