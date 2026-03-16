"""Tests for database initialization, schema, and seeding."""

import pytest

from app.db import get_db, close_db, seed_defaults


@pytest.fixture
async def db(tmp_path, monkeypatch):
    """Provide a fresh database connection using a temp file."""
    import app.db.connection as conn_mod

    monkeypatch.setattr(conn_mod, "DB_PATH", tmp_path / "test.db")
    conn_mod._db = None

    db = await get_db()
    yield db

    await close_db()
    conn_mod._db = None


async def test_schema_creates_all_tables(db):
    cursor = await db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    )
    rows = await cursor.fetchall()
    table_names = {row[0] for row in rows}
    expected = {
        "users_profile",
        "watchlist",
        "positions",
        "trades",
        "portfolio_snapshots",
        "chat_messages",
    }
    assert table_names == expected


async def test_default_user_profile(db):
    cursor = await db.execute(
        "SELECT id, cash_balance FROM users_profile WHERE id='default'"
    )
    row = await cursor.fetchone()
    assert row is not None
    assert row[0] == "default"
    assert row[1] == 10000.0


async def test_default_watchlist(db):
    cursor = await db.execute(
        "SELECT ticker FROM watchlist WHERE user_id='default' ORDER BY ticker"
    )
    rows = await cursor.fetchall()
    tickers = {row[0] for row in rows}
    expected = {"AAPL", "GOOGL", "MSFT", "AMZN", "TSLA", "NVDA", "META", "JPM", "V", "NFLX"}
    assert len(rows) == 10
    assert tickers == expected


async def test_wal_mode_and_busy_timeout(db):
    cursor = await db.execute("PRAGMA journal_mode")
    row = await cursor.fetchone()
    assert row[0] == "wal"

    cursor = await db.execute("PRAGMA busy_timeout")
    row = await cursor.fetchone()
    assert row[0] == 5000


async def test_singleton_returns_same_connection(tmp_path, monkeypatch):
    import app.db.connection as conn_mod

    monkeypatch.setattr(conn_mod, "DB_PATH", tmp_path / "test.db")
    conn_mod._db = None

    db1 = await get_db()
    db2 = await get_db()
    assert db1 is db2

    await close_db()
    conn_mod._db = None


async def test_seed_idempotent(db):
    # Seed again
    await seed_defaults(db)

    cursor = await db.execute("SELECT COUNT(*) FROM users_profile")
    row = await cursor.fetchone()
    assert row[0] == 1

    cursor = await db.execute("SELECT COUNT(*) FROM watchlist WHERE user_id='default'")
    row = await cursor.fetchone()
    assert row[0] == 10
