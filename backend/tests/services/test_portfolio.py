"""Tests for portfolio service layer: trade execution and portfolio viewing."""

import pytest

from app.db import get_db, close_db
from app.services.portfolio import execute_trade, get_portfolio, record_snapshot, get_portfolio_history


class MockPriceCache:
    """Simple mock that returns preset prices."""

    def __init__(self, prices: dict[str, float]):
        self._prices = prices

    def get_price(self, ticker: str) -> float | None:
        return self._prices.get(ticker)


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


@pytest.fixture
def price_cache():
    return MockPriceCache({"AAPL": 190.50, "GOOGL": 175.00, "TSLA": 250.00})


async def test_get_portfolio_empty(db, price_cache):
    """No positions returns cash=10000, total_value=10000, positions=[]."""
    result = await get_portfolio(price_cache)
    assert result["cash_balance"] == 10000.0
    assert result["total_value"] == 10000.0
    assert result["positions"] == []


async def test_get_portfolio_with_positions(db, price_cache):
    """Position with live price computes unrealized P&L and total value."""
    now = "2026-03-16T00:00:00+00:00"
    await db.execute(
        "INSERT INTO positions (user_id, ticker, quantity, avg_cost, updated_at) VALUES (?, ?, ?, ?, ?)",
        ("default", "AAPL", 10, 190.0, now),
    )
    await db.commit()

    result = await get_portfolio(price_cache)
    assert len(result["positions"]) == 1

    pos = result["positions"][0]
    assert pos["ticker"] == "AAPL"
    assert pos["quantity"] == 10
    assert pos["avg_cost"] == 190.0
    assert pos["current_price"] == 190.50
    assert pos["unrealized_pnl"] == pytest.approx(5.0, abs=0.01)

    # total_value = cash + (10 * 190.50)
    assert result["total_value"] == pytest.approx(10000.0 + 1905.0, abs=0.01)


async def test_buy_trade_new_position(db, price_cache):
    """Buy 10 AAPL at 190.50 creates position and deducts cash."""
    result, error = await execute_trade(price_cache, "AAPL", "buy", 10)
    assert error is None
    assert result["trade"]["ticker"] == "AAPL"
    assert result["trade"]["side"] == "buy"
    assert result["trade"]["quantity"] == 10
    assert result["trade"]["price"] == 190.50
    assert result["cash_balance"] == pytest.approx(10000.0 - 1905.0, abs=0.01)
    assert result["position"]["ticker"] == "AAPL"
    assert result["position"]["quantity"] == 10
    assert result["position"]["avg_cost"] == 190.50


async def test_buy_trade_existing_position(db, price_cache):
    """Buying more shares computes weighted average cost."""
    now = "2026-03-16T00:00:00+00:00"
    await db.execute(
        "INSERT INTO positions (user_id, ticker, quantity, avg_cost, updated_at) VALUES (?, ?, ?, ?, ?)",
        ("default", "AAPL", 10, 180.0, now),
    )
    await db.commit()

    result, error = await execute_trade(price_cache, "AAPL", "buy", 10)
    assert error is None
    assert result["position"]["quantity"] == 20
    # weighted avg = (10*180 + 10*190.50) / 20 = 185.25
    assert result["position"]["avg_cost"] == pytest.approx(185.25, abs=0.01)


async def test_buy_insufficient_cash(db, price_cache):
    """Buying with insufficient cash returns descriptive error."""
    # Set cash to 500
    await db.execute("UPDATE users_profile SET cash_balance = 500.0 WHERE id = 'default'")
    await db.commit()

    result, error = await execute_trade(price_cache, "AAPL", "buy", 10)
    assert result is None
    assert "Insufficient cash" in error
    assert "1905.00" in error
    assert "500.00" in error


async def test_sell_trade(db, price_cache):
    """Selling shares adds cash and updates position quantity."""
    now = "2026-03-16T00:00:00+00:00"
    await db.execute(
        "INSERT INTO positions (user_id, ticker, quantity, avg_cost, updated_at) VALUES (?, ?, ?, ?, ?)",
        ("default", "AAPL", 20, 180.0, now),
    )
    await db.commit()

    result, error = await execute_trade(price_cache, "AAPL", "sell", 10)
    assert error is None
    assert result["trade"]["side"] == "sell"
    assert result["trade"]["price"] == 190.50
    assert result["cash_balance"] == pytest.approx(10000.0 + 1905.0, abs=0.01)
    assert result["position"]["quantity"] == 10
    assert result["position"]["avg_cost"] == 180.0


async def test_sell_closes_position(db, price_cache):
    """Selling entire position returns position=None and deletes row."""
    now = "2026-03-16T00:00:00+00:00"
    await db.execute(
        "INSERT INTO positions (user_id, ticker, quantity, avg_cost, updated_at) VALUES (?, ?, ?, ?, ?)",
        ("default", "AAPL", 10, 180.0, now),
    )
    await db.commit()

    result, error = await execute_trade(price_cache, "AAPL", "sell", 10)
    assert error is None
    assert result["position"] is None

    # Verify position deleted from DB
    cursor = await db.execute(
        "SELECT * FROM positions WHERE user_id='default' AND ticker='AAPL'"
    )
    assert await cursor.fetchone() is None


async def test_sell_insufficient_shares(db, price_cache):
    """Selling more than owned returns error."""
    now = "2026-03-16T00:00:00+00:00"
    await db.execute(
        "INSERT INTO positions (user_id, ticker, quantity, avg_cost, updated_at) VALUES (?, ?, ?, ?, ?)",
        ("default", "AAPL", 5, 180.0, now),
    )
    await db.commit()

    result, error = await execute_trade(price_cache, "AAPL", "sell", 10)
    assert result is None
    assert "Insufficient shares" in error
    assert "10" in error
    assert "5" in error


async def test_sell_no_position(db, price_cache):
    """Selling with no position returns error about owning 0."""
    result, error = await execute_trade(price_cache, "AAPL", "sell", 10)
    assert result is None
    assert "Insufficient shares" in error
    assert "0" in error


async def test_trade_invalid_quantity(db, price_cache):
    """Zero or negative quantity returns validation error."""
    result, error = await execute_trade(price_cache, "AAPL", "buy", 0)
    assert result is None
    assert error is not None

    result, error = await execute_trade(price_cache, "AAPL", "buy", -5)
    assert result is None
    assert error is not None


async def test_trade_records_trade_log(db, price_cache):
    """Successful trade is recorded in the trades table."""
    result, error = await execute_trade(price_cache, "AAPL", "buy", 10)
    assert error is None

    cursor = await db.execute(
        "SELECT ticker, side, quantity, price FROM trades WHERE user_id='default'"
    )
    row = await cursor.fetchone()
    assert row is not None
    assert row[0] == "AAPL"
    assert row[1] == "buy"
    assert row[2] == 10
    assert row[3] == 190.50


async def test_record_snapshot_empty_portfolio(db, price_cache):
    """No positions: snapshot total_value equals cash (10000.0)."""
    await record_snapshot(price_cache)
    cursor = await db.execute(
        "SELECT total_value FROM portfolio_snapshots WHERE user_id = 'default'"
    )
    row = await cursor.fetchone()
    assert row is not None
    assert row[0] == 10000.0


async def test_record_snapshot_with_positions(db, price_cache):
    """Position AAPL qty=10, price=190.50, cash=8000 -> total=8000+1905=9905."""
    await db.execute("UPDATE users_profile SET cash_balance = 8000.0 WHERE id = 'default'")
    await db.execute(
        "INSERT INTO positions (user_id, ticker, quantity, avg_cost, updated_at) VALUES (?, ?, ?, ?, ?)",
        ("default", "AAPL", 10, 180.0, "2026-01-01T00:00:00+00:00"),
    )
    await db.commit()

    await record_snapshot(price_cache)
    cursor = await db.execute(
        "SELECT total_value FROM portfolio_snapshots WHERE user_id = 'default'"
    )
    row = await cursor.fetchone()
    assert row is not None
    # 8000 + 10 * 190.50 = 9905.0
    assert row[0] == pytest.approx(9905.0, abs=0.01)


async def test_record_snapshot_missing_price(db, price_cache):
    """Position with no price in cache is skipped; total uses only priced positions + cash."""
    await db.execute(
        "INSERT INTO positions (user_id, ticker, quantity, avg_cost, updated_at) VALUES (?, ?, ?, ?, ?)",
        ("default", "XYZ", 100, 50.0, "2026-01-01T00:00:00+00:00"),
    )
    await db.commit()

    await record_snapshot(price_cache)
    cursor = await db.execute(
        "SELECT total_value FROM portfolio_snapshots WHERE user_id = 'default'"
    )
    row = await cursor.fetchone()
    assert row is not None
    # XYZ has no price, so total = cash only = 10000.0
    assert row[0] == 10000.0


async def test_get_portfolio_history(db, price_cache):
    """Insert 3 snapshots, get_portfolio_history returns them ordered by recorded_at."""
    import uuid

    for i, ts in enumerate(["2026-01-01T00:00:00", "2026-01-02T00:00:00", "2026-01-03T00:00:00"]):
        await db.execute(
            "INSERT INTO portfolio_snapshots (id, user_id, total_value, recorded_at) VALUES (?, ?, ?, ?)",
            (str(uuid.uuid4()), "default", 10000.0 + i * 100, ts),
        )
    await db.commit()

    history = await get_portfolio_history()
    assert len(history) == 3
    assert history[0]["total_value"] == 10000.0
    assert history[1]["total_value"] == 10100.0
    assert history[2]["total_value"] == 10200.0
    assert history[0]["recorded_at"] < history[1]["recorded_at"]


async def test_trade_triggers_snapshot(db, price_cache):
    """Execute a trade, verify portfolio_snapshots table has a new row."""
    result, error = await execute_trade(price_cache, "AAPL", "buy", 5)
    assert error is None

    cursor = await db.execute(
        "SELECT COUNT(*) FROM portfolio_snapshots WHERE user_id = 'default'"
    )
    row = await cursor.fetchone()
    assert row[0] >= 1


async def test_buy_fractional_shares(db, price_cache):
    """Buy 2.5 shares of AAPL at 190.50, verify position and cash."""
    result, error = await execute_trade(price_cache, "AAPL", "buy", 2.5)
    assert error is None
    assert result["position"]["quantity"] == 2.5
    assert result["position"]["avg_cost"] == 190.50
    # 2.5 * 190.50 = 476.25
    assert result["cash_balance"] == pytest.approx(10000.0 - 476.25, abs=0.01)


async def test_sell_fractional_shares(db, price_cache):
    """Insert position qty=10.5, sell 3.5, verify remaining=7.0."""
    now = "2026-03-16T00:00:00+00:00"
    await db.execute(
        "INSERT INTO positions (user_id, ticker, quantity, avg_cost, updated_at) VALUES (?, ?, ?, ?, ?)",
        ("default", "AAPL", 10.5, 180.0, now),
    )
    await db.commit()

    result, error = await execute_trade(price_cache, "AAPL", "sell", 3.5)
    assert error is None
    assert result["position"]["quantity"] == 7.0
    # 3.5 * 190.50 = 666.75
    assert result["cash_balance"] == pytest.approx(10000.0 + 666.75, abs=0.01)


async def test_trade_no_price_available(db, price_cache):
    """Trade on ticker not in price_cache returns error."""
    result, error = await execute_trade(price_cache, "UNKNOWN", "buy", 10)
    assert result is None
    assert "No price available" in error


async def test_trade_invalid_side(db, price_cache):
    """Trade with side='short' returns error."""
    result, error = await execute_trade(price_cache, "AAPL", "short", 10)
    assert result is None
    assert "Invalid side" in error


async def test_buy_exactly_all_cash(db, price_cache):
    """Set cash=1905.00, buy 10 AAPL at 190.50, verify success with cash=0."""
    await db.execute("UPDATE users_profile SET cash_balance = 1905.00 WHERE id = 'default'")
    await db.commit()

    result, error = await execute_trade(price_cache, "AAPL", "buy", 10)
    assert error is None
    assert result["cash_balance"] == pytest.approx(0.0, abs=0.01)
    assert result["position"]["quantity"] == 10


async def test_sell_partial_then_close(db, price_cache):
    """Sell 5 of 10, then sell remaining 5, verify position=None on second."""
    now = "2026-03-16T00:00:00+00:00"
    await db.execute(
        "INSERT INTO positions (user_id, ticker, quantity, avg_cost, updated_at) VALUES (?, ?, ?, ?, ?)",
        ("default", "AAPL", 10, 180.0, now),
    )
    await db.commit()

    result1, error1 = await execute_trade(price_cache, "AAPL", "sell", 5)
    assert error1 is None
    assert result1["position"] is not None
    assert result1["position"]["quantity"] == 5

    result2, error2 = await execute_trade(price_cache, "AAPL", "sell", 5)
    assert error2 is None
    assert result2["position"] is None
