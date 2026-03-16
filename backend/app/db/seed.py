"""Default seed data for a fresh database."""

from datetime import datetime, timezone

DEFAULT_USER_ID = "default"
DEFAULT_CASH_BALANCE = 10000.0

DEFAULT_WATCHLIST_TICKERS = [
    "AAPL", "GOOGL", "MSFT", "AMZN", "TSLA",
    "NVDA", "META", "JPM", "V", "NFLX",
]


async def seed_default_data(db) -> None:
    """Insert default user profile and watchlist if they don't exist."""
    now = datetime.now(timezone.utc).isoformat()

    existing = await db.execute_fetchone(
        "SELECT id FROM users_profile WHERE id = ?", (DEFAULT_USER_ID,)
    )
    if existing:
        return

    await db.execute(
        "INSERT INTO users_profile (id, cash_balance, created_at) VALUES (?, ?, ?)",
        (DEFAULT_USER_ID, DEFAULT_CASH_BALANCE, now),
    )
    for ticker in DEFAULT_WATCHLIST_TICKERS:
        await db.execute(
            "INSERT OR IGNORE INTO watchlist (user_id, ticker, added_at) VALUES (?, ?, ?)",
            (DEFAULT_USER_ID, ticker, now),
        )
    await db.commit()
