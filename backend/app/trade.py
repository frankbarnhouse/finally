"""Shared trade execution logic used by both the API and LLM chat."""

from __future__ import annotations

from app.db import (
    delete_position,
    get_position,
    get_user_profile,
    insert_trade,
    update_cash_balance,
    upsert_position,
)
from app.db.connection import Database
from app.market.cache import PriceCache


async def execute_trade(
    db: Database,
    ticker: str,
    side: str,
    quantity: float,
    price_cache: PriceCache,
) -> dict:
    """Execute a market order. Returns trade result dict. Raises ValueError on failure."""
    ticker = ticker.upper()
    side = side.lower()

    if side not in ("buy", "sell"):
        raise ValueError("Side must be 'buy' or 'sell'")
    if quantity <= 0:
        raise ValueError("Quantity must be greater than 0")

    current_price = price_cache.get_price(ticker)
    if current_price is None:
        raise ValueError(f"No price available for {ticker}")

    profile = await get_user_profile(db)
    cash = profile["cash_balance"]

    if side == "buy":
        cost = round(current_price * quantity, 2)
        if cost > cash:
            raise ValueError(
                f"Insufficient cash: need ${cost:.2f} but only ${cash:.2f} available"
            )
        new_cash = round(cash - cost, 2)
        await update_cash_balance(db, new_cash)

        existing = await get_position(db, ticker)
        if existing:
            total_qty = existing["quantity"] + quantity
            total_cost = existing["avg_cost"] * existing["quantity"] + current_price * quantity
            new_avg = round(total_cost / total_qty, 2)
            await upsert_position(db, ticker, total_qty, new_avg)
            position_resp = {"ticker": ticker, "quantity": total_qty, "avg_cost": new_avg}
        else:
            await upsert_position(db, ticker, quantity, current_price)
            position_resp = {"ticker": ticker, "quantity": quantity, "avg_cost": current_price}

    else:  # sell
        existing = await get_position(db, ticker)
        if not existing:
            raise ValueError(f"No position in {ticker} to sell")
        if quantity > existing["quantity"]:
            raise ValueError(
                f"Insufficient shares: have {existing['quantity']} but trying to sell {quantity}"
            )
        proceeds = round(current_price * quantity, 2)
        new_cash = round(cash + proceeds, 2)
        await update_cash_balance(db, new_cash)

        remaining = existing["quantity"] - quantity
        if remaining > 0:
            await upsert_position(db, ticker, remaining, existing["avg_cost"])
            position_resp = {"ticker": ticker, "quantity": remaining, "avg_cost": existing["avg_cost"]}
        else:
            await delete_position(db, ticker)
            position_resp = None

    trade = await insert_trade(db, ticker, side, quantity, current_price)

    return {
        "trade": {
            "ticker": trade["ticker"],
            "side": trade["side"],
            "quantity": trade["quantity"],
            "price": trade["price"],
            "executed_at": trade["executed_at"],
        },
        "cash_balance": new_cash,
        "position": position_resp,
    }
