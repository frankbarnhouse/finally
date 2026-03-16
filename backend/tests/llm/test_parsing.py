"""Tests for LLM response parsing."""

from app.llm.chat import _parse_llm_response


class TestParseLlmResponse:
    def test_valid_full_response(self):
        raw = '{"message": "Done!", "trades": [{"ticker": "AAPL", "side": "buy", "quantity": 10}], "watchlist_changes": [{"ticker": "PYPL", "action": "add"}]}'
        result = _parse_llm_response(raw)
        assert result["message"] == "Done!"
        assert len(result["trades"]) == 1
        assert result["trades"][0] == {"ticker": "AAPL", "side": "buy", "quantity": 10}
        assert len(result["watchlist_changes"]) == 1

    def test_message_only(self):
        raw = '{"message": "Hello!"}'
        result = _parse_llm_response(raw)
        assert result["message"] == "Hello!"
        assert result["trades"] == []
        assert result["watchlist_changes"] == []

    def test_invalid_json_returns_raw_message(self):
        raw = "This is not JSON"
        result = _parse_llm_response(raw)
        assert result["message"] == "This is not JSON"
        assert result["trades"] == []

    def test_invalid_trade_side_filtered(self):
        raw = '{"message": "ok", "trades": [{"ticker": "AAPL", "side": "hold", "quantity": 10}]}'
        result = _parse_llm_response(raw)
        assert result["trades"] == []

    def test_negative_quantity_filtered(self):
        raw = '{"message": "ok", "trades": [{"ticker": "AAPL", "side": "buy", "quantity": -5}]}'
        result = _parse_llm_response(raw)
        assert result["trades"] == []

    def test_zero_quantity_filtered(self):
        raw = '{"message": "ok", "trades": [{"ticker": "AAPL", "side": "buy", "quantity": 0}]}'
        result = _parse_llm_response(raw)
        assert result["trades"] == []

    def test_missing_trade_fields_filtered(self):
        raw = '{"message": "ok", "trades": [{"ticker": "AAPL"}]}'
        result = _parse_llm_response(raw)
        assert result["trades"] == []

    def test_invalid_watchlist_action_filtered(self):
        raw = '{"message": "ok", "watchlist_changes": [{"ticker": "AAPL", "action": "watch"}]}'
        result = _parse_llm_response(raw)
        assert result["watchlist_changes"] == []

    def test_ticker_uppercased(self):
        raw = '{"message": "ok", "trades": [{"ticker": "aapl", "side": "buy", "quantity": 5}]}'
        result = _parse_llm_response(raw)
        assert result["trades"][0]["ticker"] == "AAPL"

    def test_empty_string_returns_fallback(self):
        result = _parse_llm_response("")
        assert "trouble" in result["message"].lower()

    def test_multiple_trades(self):
        raw = '{"message": "ok", "trades": [{"ticker": "AAPL", "side": "buy", "quantity": 5}, {"ticker": "MSFT", "side": "sell", "quantity": 3}]}'
        result = _parse_llm_response(raw)
        assert len(result["trades"]) == 2
