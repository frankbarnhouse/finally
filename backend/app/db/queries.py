"""Async CRUD functions for all database tables."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from .connection import Database


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _uuid() -> str:
    return str(uuid.uuid4())


# --- Users Profile ---

async def get_user_profile(db: Database, user_id: str = "default") -> dict | None:
    row = await db.execute_fetchone(
        "SELECT id, cash_balance, created_at FROM users_profile WHERE id = ?", (user_id,)
    )
    return dict(row) if row else None


async def update_cash_balance(db: Database, cash_balance: float, user_id: str = "default") -> None:
    await db.execute(
        "UPDATE users_profile SET cash_balance = ? WHERE id = ?", (cash_balance, user_id)
    )
    await db.commit()


# --- Watchlist ---

async def get_watchlist(db: Database, user_id: str = "default") -> list[dict]:
    rows = await db.execute_fetchall(
        "SELECT user_id, ticker, added_at FROM watchlist WHERE user_id = ? ORDER BY added_at",
        (user_id,),
    )
    return [dict(r) for r in rows]


async def add_to_watchlist(db: Database, ticker: str, user_id: str = "default") -> dict:
    now = _now()
    await db.execute(
        "INSERT OR IGNORE INTO watchlist (user_id, ticker, added_at) VALUES (?, ?, ?)",
        (user_id, ticker.upper(), now),
    )
    await db.commit()
    return {"user_id": user_id, "ticker": ticker.upper(), "added_at": now}


async def remove_from_watchlist(db: Database, ticker: str, user_id: str = "default") -> bool:
    cursor = await db.execute(
        "DELETE FROM watchlist WHERE user_id = ? AND ticker = ?", (user_id, ticker.upper())
    )
    await db.commit()
    return cursor.rowcount > 0


# --- Positions ---

async def get_positions(db: Database, user_id: str = "default") -> list[dict]:
    rows = await db.execute_fetchall(
        "SELECT user_id, ticker, quantity, avg_cost, updated_at FROM positions WHERE user_id = ?",
        (user_id,),
    )
    return [dict(r) for r in rows]


async def get_position(db: Database, ticker: str, user_id: str = "default") -> dict | None:
    row = await db.execute_fetchone(
        "SELECT user_id, ticker, quantity, avg_cost, updated_at FROM positions "
        "WHERE user_id = ? AND ticker = ?",
        (user_id, ticker.upper()),
    )
    return dict(row) if row else None


async def upsert_position(
    db: Database, ticker: str, quantity: float, avg_cost: float, user_id: str = "default"
) -> dict:
    now = _now()
    await db.execute(
        "INSERT INTO positions (user_id, ticker, quantity, avg_cost, updated_at) "
        "VALUES (?, ?, ?, ?, ?) "
        "ON CONFLICT(user_id, ticker) DO UPDATE SET quantity=?, avg_cost=?, updated_at=?",
        (user_id, ticker.upper(), quantity, avg_cost, now, quantity, avg_cost, now),
    )
    await db.commit()
    return {"user_id": user_id, "ticker": ticker.upper(), "quantity": quantity,
            "avg_cost": avg_cost, "updated_at": now}


async def delete_position(db: Database, ticker: str, user_id: str = "default") -> bool:
    cursor = await db.execute(
        "DELETE FROM positions WHERE user_id = ? AND ticker = ?", (user_id, ticker.upper())
    )
    await db.commit()
    return cursor.rowcount > 0


# --- Trades ---

async def insert_trade(
    db: Database, ticker: str, side: str, quantity: float, price: float,
    user_id: str = "default",
) -> dict:
    trade_id = _uuid()
    now = _now()
    await db.execute(
        "INSERT INTO trades (id, user_id, ticker, side, quantity, price, executed_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (trade_id, user_id, ticker.upper(), side, quantity, price, now),
    )
    await db.commit()
    return {"id": trade_id, "user_id": user_id, "ticker": ticker.upper(), "side": side,
            "quantity": quantity, "price": price, "executed_at": now}


async def get_trades(db: Database, user_id: str = "default", limit: int = 50) -> list[dict]:
    rows = await db.execute_fetchall(
        "SELECT id, user_id, ticker, side, quantity, price, executed_at FROM trades "
        "WHERE user_id = ? ORDER BY executed_at DESC LIMIT ?",
        (user_id, limit),
    )
    return [dict(r) for r in rows]


# --- Portfolio Snapshots ---

async def insert_snapshot(
    db: Database, total_value: float, user_id: str = "default"
) -> dict:
    snap_id = _uuid()
    now = _now()
    await db.execute(
        "INSERT INTO portfolio_snapshots (id, user_id, total_value, recorded_at) "
        "VALUES (?, ?, ?, ?)",
        (snap_id, user_id, total_value, now),
    )
    await db.commit()
    return {"id": snap_id, "user_id": user_id, "total_value": total_value, "recorded_at": now}


async def get_snapshots(db: Database, user_id: str = "default", limit: int = 500) -> list[dict]:
    rows = await db.execute_fetchall(
        "SELECT id, user_id, total_value, recorded_at FROM portfolio_snapshots "
        "WHERE user_id = ? ORDER BY recorded_at ASC LIMIT ?",
        (user_id, limit),
    )
    return [dict(r) for r in rows]


# --- Chat Messages ---

async def insert_chat_message(
    db: Database, role: str, content: str, actions: str | None = None,
    user_id: str = "default",
) -> dict:
    msg_id = _uuid()
    now = _now()
    await db.execute(
        "INSERT INTO chat_messages (id, user_id, role, content, actions, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (msg_id, user_id, role, content, actions, now),
    )
    await db.commit()
    return {"id": msg_id, "user_id": user_id, "role": role, "content": content,
            "actions": actions, "created_at": now}


async def get_chat_messages(
    db: Database, user_id: str = "default", limit: int = 10
) -> list[dict]:
    rows = await db.execute_fetchall(
        "SELECT id, user_id, role, content, actions, created_at FROM chat_messages "
        "WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
        (user_id, limit),
    )
    return [dict(r) for r in reversed(rows)]
