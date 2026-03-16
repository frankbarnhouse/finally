"""Default data seeding for FinAlly."""

from datetime import datetime, timezone

import aiosqlite

DEFAULT_TICKERS = [
    "AAPL", "GOOGL", "MSFT", "AMZN", "TSLA",
    "NVDA", "META", "JPM", "V", "NFLX",
]


async def seed_defaults(db: aiosqlite.Connection) -> None:
    """Seed default user profile and watchlist. Idempotent via INSERT OR IGNORE."""
    now = datetime.now(timezone.utc).isoformat()

    await db.execute(
        "INSERT OR IGNORE INTO users_profile (id, cash_balance, created_at) VALUES (?, ?, ?)",
        ("default", 10000.0, now),
    )

    for ticker in DEFAULT_TICKERS:
        await db.execute(
            "INSERT OR IGNORE INTO watchlist (user_id, ticker, added_at) VALUES (?, ?, ?)",
            ("default", ticker, now),
        )

    await db.commit()
