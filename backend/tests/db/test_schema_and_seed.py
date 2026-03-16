"""Tests for schema creation and seed data."""

from app.db import DEFAULT_CASH_BALANCE, DEFAULT_USER_ID, DEFAULT_WATCHLIST_TICKERS


async def test_tables_created(db):
    """All six tables should exist after connect."""
    rows = await db.execute_fetchall(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    )
    table_names = sorted(r["name"] for r in rows)
    expected = sorted([
        "chat_messages", "portfolio_snapshots", "positions",
        "trades", "users_profile", "watchlist",
    ])
    assert table_names == expected


async def test_default_user_seeded(db):
    """Default user profile should exist with $10k."""
    row = await db.execute_fetchone(
        "SELECT id, cash_balance FROM users_profile WHERE id = ?", (DEFAULT_USER_ID,)
    )
    assert row is not None
    assert row["id"] == DEFAULT_USER_ID
    assert row["cash_balance"] == DEFAULT_CASH_BALANCE


async def test_default_watchlist_seeded(db):
    """Default watchlist should have 10 tickers."""
    rows = await db.execute_fetchall(
        "SELECT ticker FROM watchlist WHERE user_id = ?", (DEFAULT_USER_ID,)
    )
    tickers = [r["ticker"] for r in rows]
    assert sorted(tickers) == sorted(DEFAULT_WATCHLIST_TICKERS)


async def test_seed_is_idempotent(db):
    """Calling connect again should not duplicate seed data."""
    from app.db.seed import seed_default_data
    await seed_default_data(db)

    rows = await db.execute_fetchall("SELECT id FROM users_profile")
    assert len(rows) == 1
