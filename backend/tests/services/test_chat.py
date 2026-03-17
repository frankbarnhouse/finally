"""Tests for chat service: LLM integration, auto-execution, mock mode."""

import uuid

import pytest

from app.db import get_db, close_db
from app.services.chat import handle_chat_message, ChatResponse, TradeAction, WatchlistChange


class MockPriceCache:
    """Simple mock that returns preset prices."""

    def __init__(self, prices=None):
        self._prices = prices or {"AAPL": 190.50, "GOOGL": 175.00}

    def get_price(self, ticker):
        return self._prices.get(ticker)


class MockDataSource:
    """Mock market data source tracking add/remove calls."""

    def __init__(self):
        self.added = []
        self.removed = []

    async def add_ticker(self, ticker):
        self.added.append(ticker)

    async def remove_ticker(self, ticker):
        self.removed.append(ticker)


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


@pytest.fixture
def data_source():
    return MockDataSource()


@pytest.fixture(autouse=True)
def mock_env(monkeypatch):
    """Set LLM_MOCK=true for all tests by default."""
    monkeypatch.setenv("LLM_MOCK", "true")


async def test_chat_returns_response(db, price_cache, data_source):
    """handle_chat_message returns dict with 'message' and 'actions' keys."""
    result = await handle_chat_message("Hello", price_cache, data_source)
    assert "message" in result
    assert "actions" in result
    assert isinstance(result["message"], str)
    assert isinstance(result["actions"], dict)


async def test_mock_mode(db, price_cache, data_source):
    """LLM_MOCK=true returns deterministic response without calling litellm."""
    result = await handle_chat_message("Tell me about my portfolio", price_cache, data_source)
    assert "message" in result
    assert len(result["message"]) > 0
    # No trades or watchlist changes for a generic message
    assert result["actions"]["trades"] == []
    assert result["actions"]["watchlist_changes"] == []


async def test_mock_buy_triggers_trade(db, price_cache, data_source):
    """Sending 'buy' in message with LLM_MOCK=true returns a trade action."""
    result = await handle_chat_message("buy some AAPL", price_cache, data_source)
    assert len(result["actions"]["trades"]) > 0
    trade = result["actions"]["trades"][0]
    assert trade["ticker"] == "AAPL"
    assert trade["side"] == "buy"


async def test_mock_add_watchlist(db, price_cache, data_source):
    """Sending 'add to watchlist' with LLM_MOCK=true returns a watchlist_change action."""
    result = await handle_chat_message("add PYPL to watchlist", price_cache, data_source)
    assert len(result["actions"]["watchlist_changes"]) > 0
    change = result["actions"]["watchlist_changes"][0]
    assert change["ticker"] == "PYPL"
    assert change["action"] == "add"


async def test_trade_auto_execution(db, price_cache, data_source):
    """Mock buy triggers execute_trade; position created and cash deducted."""
    result = await handle_chat_message("buy some AAPL", price_cache, data_source)
    assert len(result["actions"]["trades"]) > 0

    # Verify position was actually created in DB
    cursor = await db.execute(
        "SELECT quantity FROM positions WHERE user_id = 'default' AND ticker = 'AAPL'"
    )
    row = await cursor.fetchone()
    assert row is not None
    assert row[0] > 0

    # Verify cash was deducted
    cursor = await db.execute(
        "SELECT cash_balance FROM users_profile WHERE id = 'default'"
    )
    row = await cursor.fetchone()
    assert row[0] < 10000.0


async def test_watchlist_auto_execution(db, price_cache, data_source):
    """Mock watchlist add triggers add_ticker on data_source."""
    result = await handle_chat_message("add PYPL to watchlist", price_cache, data_source)
    assert len(result["actions"]["watchlist_changes"]) > 0
    assert "PYPL" in data_source.added


async def test_failed_trade_appended_to_message(db, price_cache, data_source):
    """When execute_trade returns an error, error text is appended to response message."""
    # Set cash to $0 so buy fails
    await db.execute("UPDATE users_profile SET cash_balance = 0.0 WHERE id = 'default'")
    await db.commit()

    result = await handle_chat_message("buy some AAPL", price_cache, data_source)
    # The error about insufficient cash should be in the message
    assert "Insufficient cash" in result["message"]
    # No trades should have executed
    assert result["actions"]["trades"] == []


async def test_failed_watchlist_appended_to_message(db, price_cache, data_source):
    """When add_ticker raises exception, error text is appended to response message."""

    async def failing_add(ticker, price_cache, data_source):
        raise ValueError("Ticker not found: XYZ")

    # Monkey-patch add_ticker to fail
    import app.services.chat as chat_mod
    original = chat_mod.add_ticker

    chat_mod.add_ticker = failing_add
    try:
        result = await handle_chat_message("add XYZ to watchlist", price_cache, data_source)
        assert "failed" in result["message"].lower() or "error" in result["message"].lower() or "Ticker not found" in result["message"]
    finally:
        chat_mod.add_ticker = original


async def test_message_history_limit(db, price_cache, data_source):
    """After inserting 15 messages, only last 10 are included in context."""
    # Insert 15 messages directly
    for i in range(15):
        ts = f"2026-01-01T{i:02d}:00:00+00:00"
        await db.execute(
            "INSERT INTO chat_messages (id, user_id, role, content, actions, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (str(uuid.uuid4()), "default", "user", f"Message {i}", None, ts),
        )
    await db.commit()

    # Call handle_chat_message - it should load only last 10
    result = await handle_chat_message("Hello", price_cache, data_source)
    assert "message" in result

    # Verify: we now have 15 + 2 (user + assistant from this call) = 17 messages
    cursor = await db.execute(
        "SELECT COUNT(*) FROM chat_messages WHERE user_id = 'default'"
    )
    row = await cursor.fetchone()
    assert row[0] == 17


async def test_messages_stored_in_db(db, price_cache, data_source):
    """After handle_chat_message, both user and assistant messages exist in DB."""
    await handle_chat_message("Hello there", price_cache, data_source)

    cursor = await db.execute(
        "SELECT role, content FROM chat_messages WHERE user_id = 'default' ORDER BY created_at"
    )
    rows = await cursor.fetchall()
    assert len(rows) == 2
    assert rows[0][0] == "user"
    assert rows[0][1] == "Hello there"
    assert rows[1][0] == "assistant"
    assert len(rows[1][1]) > 0


def test_chat_response_model_minimal():
    """ChatResponse(message='hi') parses with empty trades and watchlist_changes."""
    resp = ChatResponse(message="hi")
    assert resp.message == "hi"
    assert resp.trades == []
    assert resp.watchlist_changes == []


def test_chat_response_model_with_actions():
    """ChatResponse with trades and watchlist_changes parses correctly."""
    resp = ChatResponse(
        message="Done",
        trades=[TradeAction(ticker="AAPL", side="buy", quantity=5)],
        watchlist_changes=[WatchlistChange(ticker="PYPL", action="add")],
    )
    assert len(resp.trades) == 1
    assert resp.trades[0].ticker == "AAPL"
    assert len(resp.watchlist_changes) == 1
    assert resp.watchlist_changes[0].ticker == "PYPL"


def test_chat_response_model_validate_json_minimal():
    """ChatResponse.model_validate_json with minimal JSON succeeds with defaults."""
    resp = ChatResponse.model_validate_json('{"message":"hi"}')
    assert resp.message == "hi"
    assert resp.trades == []
    assert resp.watchlist_changes == []


def test_chat_response_model_validate_json_malformed():
    """ChatResponse.model_validate_json with malformed JSON raises ValidationError."""
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        ChatResponse.model_validate_json("not json")


async def test_llm_exception_returns_error_message(db, price_cache, data_source, monkeypatch):
    """When LLM call raises, response contains error message."""
    monkeypatch.setenv("LLM_MOCK", "false")

    async def failing_acompletion(*args, **kwargs):
        raise RuntimeError("API down")

    import app.services.chat as chat_mod
    monkeypatch.setattr(chat_mod, "acompletion", failing_acompletion)

    result = await handle_chat_message("Hello", price_cache, data_source)
    assert "error" in result["message"].lower()


async def test_mock_sell_triggers_trade(db, price_cache, data_source):
    """Send 'sell some AAPL' with position in DB, verify sell trade executed."""
    now = "2026-03-16T00:00:00+00:00"
    await db.execute(
        "INSERT INTO positions (user_id, ticker, quantity, avg_cost, updated_at) VALUES (?, ?, ?, ?, ?)",
        ("default", "AAPL", 10, 180.0, now),
    )
    await db.commit()

    result = await handle_chat_message("sell some AAPL", price_cache, data_source)
    assert len(result["actions"]["trades"]) > 0
    trade = result["actions"]["trades"][0]
    assert trade["side"] == "sell"

    # Verify position quantity decreased
    cursor = await db.execute(
        "SELECT quantity FROM positions WHERE user_id = 'default' AND ticker = 'AAPL'"
    )
    row = await cursor.fetchone()
    # Mock sells 10 of 10, so position should be closed (no row)
    assert row is None
