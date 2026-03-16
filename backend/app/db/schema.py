"""Database schema definitions for FinAlly."""

import aiosqlite

TABLES = [
    """CREATE TABLE IF NOT EXISTS users_profile (
        id TEXT PRIMARY KEY DEFAULT 'default',
        cash_balance REAL NOT NULL DEFAULT 10000.0,
        created_at TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS watchlist (
        user_id TEXT NOT NULL DEFAULT 'default',
        ticker TEXT NOT NULL,
        added_at TEXT NOT NULL,
        UNIQUE(user_id, ticker)
    )""",
    """CREATE TABLE IF NOT EXISTS positions (
        user_id TEXT NOT NULL DEFAULT 'default',
        ticker TEXT NOT NULL,
        quantity REAL NOT NULL,
        avg_cost REAL NOT NULL,
        updated_at TEXT NOT NULL,
        UNIQUE(user_id, ticker)
    )""",
    """CREATE TABLE IF NOT EXISTS trades (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL DEFAULT 'default',
        ticker TEXT NOT NULL,
        side TEXT NOT NULL CHECK(side IN ('buy', 'sell')),
        quantity REAL NOT NULL,
        price REAL NOT NULL,
        executed_at TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS portfolio_snapshots (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL DEFAULT 'default',
        total_value REAL NOT NULL,
        recorded_at TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS chat_messages (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL DEFAULT 'default',
        role TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
        content TEXT NOT NULL,
        actions TEXT,
        created_at TEXT NOT NULL
    )""",
]


async def init_schema(db: aiosqlite.Connection) -> None:
    """Create all tables if they don't exist."""
    for sql in TABLES:
        await db.execute(sql)
    await db.commit()
