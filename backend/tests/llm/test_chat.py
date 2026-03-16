"""Tests for the chat handler with mock mode."""

import os

from app.db import get_chat_messages, get_watchlist
from app.llm.chat import handle_chat_message
from app.trade import execute_trade


async def _trade_fn(db, ticker, side, quantity, price_cache):
    return await execute_trade(db, ticker, side, quantity, price_cache)


class TestHandleChatMessage:
    async def test_mock_mode_default_response(self, db, price_cache, monkeypatch):
        monkeypatch.setenv("LLM_MOCK", "true")
        result = await handle_chat_message("hello", db, price_cache, _trade_fn)
        assert "message" in result
        assert result["trades"] == []
        assert result["watchlist_changes"] == []

    async def test_mock_buy_executes_trade(self, db, price_cache, monkeypatch):
        monkeypatch.setenv("LLM_MOCK", "true")
        result = await handle_chat_message("buy 5 shares of AAPL", db, price_cache, _trade_fn)
        assert len(result["trades"]) == 1
        trade = result["trades"][0]["trade"]
        assert trade["ticker"] == "AAPL"
        assert trade["side"] == "buy"
        assert trade["quantity"] == 5

    async def test_mock_sell_without_position_appends_error(self, db, price_cache, monkeypatch):
        monkeypatch.setenv("LLM_MOCK", "true")
        result = await handle_chat_message("sell 5 shares of AAPL", db, price_cache, _trade_fn)
        assert result["trades"] == []
        assert "Trade failed" in result["message"]

    async def test_mock_add_to_watchlist(self, db, price_cache, monkeypatch):
        monkeypatch.setenv("LLM_MOCK", "true")
        result = await handle_chat_message(
            "add PYPL to the watchlist", db, price_cache, _trade_fn
        )
        assert len(result["watchlist_changes"]) == 1
        assert result["watchlist_changes"][0]["ticker"] == "PYPL"
        # Verify in DB
        wl = await get_watchlist(db)
        tickers = [w["ticker"] for w in wl]
        assert "PYPL" in tickers

    async def test_messages_stored_in_db(self, db, price_cache, monkeypatch):
        monkeypatch.setenv("LLM_MOCK", "true")
        await handle_chat_message("hello", db, price_cache, _trade_fn)
        messages = await get_chat_messages(db)
        assert len(messages) == 2  # user + assistant
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == "hello"
        assert messages[1]["role"] == "assistant"

    async def test_mock_buy_insufficient_cash(self, db, price_cache, monkeypatch):
        """Buy too many shares should fail gracefully."""
        monkeypatch.setenv("LLM_MOCK", "true")
        # AAPL is at $190.50, buying 1000 shares = $190,500 > $10,000 cash
        result = await handle_chat_message(
            "buy 1000 shares of AAPL", db, price_cache, _trade_fn
        )
        assert result["trades"] == []
        assert "Insufficient cash" in result["message"]
