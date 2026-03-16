"""Portfolio service: trade execution and portfolio valuation."""

import uuid
from datetime import datetime, timezone

from app.db import get_db


async def get_portfolio(price_cache) -> dict:
    """Return current portfolio state with live P&L."""
    db = await get_db()

    cursor = await db.execute(
        "SELECT cash_balance FROM users_profile WHERE id = ?", ("default",)
    )
    row = await cursor.fetchone()
    cash = row[0] if row else 0.0

    cursor = await db.execute(
        "SELECT ticker, quantity, avg_cost FROM positions WHERE user_id = ?", ("default",)
    )
    rows = await cursor.fetchall()

    positions = []
    total_position_value = 0.0
    for r in rows:
        ticker, quantity, avg_cost = r[0], r[1], r[2]
        current_price = price_cache.get_price(ticker)
        if current_price is None:
            current_price = avg_cost  # fallback if no live price
        unrealized_pnl = round((current_price - avg_cost) * quantity, 2)
        position_value = quantity * current_price
        total_position_value += position_value
        positions.append({
            "ticker": ticker,
            "quantity": quantity,
            "avg_cost": avg_cost,
            "current_price": current_price,
            "unrealized_pnl": unrealized_pnl,
        })

    return {
        "positions": positions,
        "cash_balance": cash,
        "total_value": round(cash + total_position_value, 2),
    }


async def execute_trade(
    price_cache, ticker: str, side: str, quantity: float
) -> tuple[dict | None, str | None]:
    """Execute a market order. Returns (result, error)."""
    if quantity <= 0:
        return None, f"Invalid quantity: {quantity}. Must be greater than 0"

    db = await get_db()
    price = price_cache.get_price(ticker)
    if price is None:
        return None, f"No price available for {ticker}"

    await db.execute("BEGIN IMMEDIATE")
    try:
        cursor = await db.execute(
            "SELECT cash_balance FROM users_profile WHERE id = ?", ("default",)
        )
        row = await cursor.fetchone()
        cash = row[0] if row else 0.0

        if side == "buy":
            cost = round(quantity * price, 2)
            if cash < cost:
                await db.execute("ROLLBACK")
                return None, f"Insufficient cash: need ${cost:.2f} but only ${cash:.2f} available"

            new_cash = round(cash - cost, 2)
            await db.execute(
                "UPDATE users_profile SET cash_balance = ? WHERE id = ?", (new_cash, "default")
            )

            cursor = await db.execute(
                "SELECT quantity, avg_cost FROM positions WHERE user_id = ? AND ticker = ?",
                ("default", ticker),
            )
            existing = await cursor.fetchone()
            now = datetime.now(timezone.utc).isoformat()

            if existing:
                old_qty, old_avg = existing[0], existing[1]
                new_qty = old_qty + quantity
                new_avg = round((old_qty * old_avg + quantity * price) / new_qty, 2)
                await db.execute(
                    "UPDATE positions SET quantity = ?, avg_cost = ?, updated_at = ? "
                    "WHERE user_id = ? AND ticker = ?",
                    (new_qty, new_avg, now, "default", ticker),
                )
                position_result = {"ticker": ticker, "quantity": new_qty, "avg_cost": new_avg}
            else:
                await db.execute(
                    "INSERT INTO positions (user_id, ticker, quantity, avg_cost, updated_at) "
                    "VALUES (?, ?, ?, ?, ?)",
                    ("default", ticker, quantity, price, now),
                )
                position_result = {"ticker": ticker, "quantity": quantity, "avg_cost": price}

        elif side == "sell":
            cursor = await db.execute(
                "SELECT quantity, avg_cost FROM positions WHERE user_id = ? AND ticker = ?",
                ("default", ticker),
            )
            existing = await cursor.fetchone()

            if not existing or existing[0] < quantity:
                owned = existing[0] if existing else 0
                await db.execute("ROLLBACK")
                return None, (
                    f"Insufficient shares: want to sell {quantity:g} "
                    f"but only own {owned:g}"
                )

            proceeds = round(quantity * price, 2)
            new_cash = round(cash + proceeds, 2)
            await db.execute(
                "UPDATE users_profile SET cash_balance = ? WHERE id = ?", (new_cash, "default")
            )

            remaining = existing[0] - quantity
            now = datetime.now(timezone.utc).isoformat()

            if remaining == 0:
                await db.execute(
                    "DELETE FROM positions WHERE user_id = ? AND ticker = ?",
                    ("default", ticker),
                )
                position_result = None
            else:
                await db.execute(
                    "UPDATE positions SET quantity = ?, updated_at = ? "
                    "WHERE user_id = ? AND ticker = ?",
                    (remaining, now, "default", ticker),
                )
                position_result = {
                    "ticker": ticker,
                    "quantity": remaining,
                    "avg_cost": existing[1],
                }
        else:
            await db.execute("ROLLBACK")
            return None, f"Invalid side: {side}. Must be 'buy' or 'sell'"

        trade_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        await db.execute(
            "INSERT INTO trades (id, user_id, ticker, side, quantity, price, executed_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (trade_id, "default", ticker, side, quantity, price, now),
        )

        await db.execute("COMMIT")

        await record_snapshot(price_cache)

        return {
            "trade": {
                "ticker": ticker,
                "side": side,
                "quantity": quantity,
                "price": price,
                "executed_at": now,
            },
            "cash_balance": new_cash,
            "position": position_result,
        }, None

    except Exception:
        await db.execute("ROLLBACK")
        raise


async def record_snapshot(price_cache) -> None:
    """Calculate and store current portfolio total value."""
    db = await get_db()
    user_id = "default"
    cursor = await db.execute(
        "SELECT cash_balance FROM users_profile WHERE id = ?", (user_id,)
    )
    row = await cursor.fetchone()
    cash = row[0]

    cursor = await db.execute(
        "SELECT ticker, quantity FROM positions WHERE user_id = ?", (user_id,)
    )
    positions = await cursor.fetchall()

    total = cash
    for pos in positions:
        price = price_cache.get_price(pos[0])
        if price is not None:
            total += pos[1] * price

    now = datetime.now(timezone.utc).isoformat()
    await db.execute(
        "INSERT INTO portfolio_snapshots (id, user_id, total_value, recorded_at) VALUES (?, ?, ?, ?)",
        (str(uuid.uuid4()), user_id, round(total, 2), now),
    )
    await db.commit()


async def get_portfolio_history() -> list[dict]:
    """Return portfolio value snapshots ordered by time."""
    db = await get_db()
    cursor = await db.execute(
        "SELECT total_value, recorded_at FROM portfolio_snapshots WHERE user_id = ? ORDER BY recorded_at ASC",
        ("default",),
    )
    rows = await cursor.fetchall()
    return [{"total_value": row[0], "recorded_at": row[1]} for row in rows]
