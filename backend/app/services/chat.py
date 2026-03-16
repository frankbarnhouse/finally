"""Chat service: LLM integration with portfolio context and auto-execution."""

from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import datetime, timezone

from litellm import acompletion
from pydantic import BaseModel, Field

from app.db import get_db
from app.services.portfolio import execute_trade, get_portfolio
from app.services.watchlist import add_ticker, get_watchlist, remove_ticker

log = logging.getLogger(__name__)


class TradeAction(BaseModel):
    ticker: str
    side: str
    quantity: float


class WatchlistChange(BaseModel):
    ticker: str
    action: str  # "add" or "remove"


class ChatResponse(BaseModel):
    message: str
    trades: list[TradeAction] = Field(default_factory=list)
    watchlist_changes: list[WatchlistChange] = Field(default_factory=list)


SYSTEM_PROMPT = """You are FinAlly, an AI trading assistant for a simulated portfolio.

You can analyze the user's portfolio, suggest trades, and execute trades when asked.
You can also manage the watchlist by adding or removing tickers.

Always respond with valid JSON matching the required schema:
- "message": Your conversational response
- "trades": Array of trades to execute [{ticker, side, quantity}]
- "watchlist_changes": Array of watchlist changes [{ticker, action}]
  where action is "add" or "remove"

Be concise and data-driven. When the user asks you to trade, include the trade in your response.
When suggesting trades, explain your reasoning briefly."""


def format_portfolio_context(portfolio: dict, watchlist: list[dict]) -> str:
    """Format portfolio and watchlist state into a readable context block."""
    positions_text = "\n".join(
        f"  {p['ticker']}: {p['quantity']} shares @ ${p['avg_cost']:.2f} "
        f"(current: ${p['current_price']:.2f}, P&L: ${p['unrealized_pnl']:.2f})"
        for p in portfolio["positions"]
    ) or "  No positions"

    watchlist_text = ", ".join(
        f"{w['ticker']}=${w['price']:.2f}" if w["price"] else w["ticker"]
        for w in watchlist
    ) or "Empty"

    return (
        f"PORTFOLIO STATE:\n"
        f"Cash: ${portfolio['cash_balance']:.2f}\n"
        f"Total Value: ${portfolio['total_value']:.2f}\n"
        f"Positions:\n{positions_text}\n"
        f"Watchlist: {watchlist_text}"
    )


def mock_response(user_message: str) -> ChatResponse:
    """Return deterministic mock response for testing."""
    msg = user_message.lower()
    if "buy" in msg:
        return ChatResponse(
            message="Mock: Executing buy order as requested.",
            trades=[TradeAction(ticker="AAPL", side="buy", quantity=10)],
        )
    if "sell" in msg:
        return ChatResponse(
            message="Mock: Executing sell order as requested.",
            trades=[TradeAction(ticker="AAPL", side="sell", quantity=10)],
        )
    if "add" in msg and "watchlist" in msg:
        return ChatResponse(
            message="Mock: Adding ticker to watchlist.",
            watchlist_changes=[WatchlistChange(ticker="PYPL", action="add")],
        )
    if "remove" in msg and "watchlist" in msg:
        return ChatResponse(
            message="Mock: Removing ticker from watchlist.",
            watchlist_changes=[WatchlistChange(ticker="PYPL", action="remove")],
        )
    return ChatResponse(
        message="Mock: I can help you with your portfolio. You have positions and cash available for trading.",
    )


async def handle_chat_message(
    user_message: str,
    price_cache,
    data_source,
) -> dict:
    """Orchestrate the full chat flow: context, LLM call, action execution, storage."""
    portfolio = await get_portfolio(price_cache)
    watchlist = await get_watchlist(price_cache)

    db = await get_db()
    cursor = await db.execute(
        "SELECT role, content FROM chat_messages WHERE user_id = ? "
        "ORDER BY created_at DESC LIMIT 10",
        ("default",),
    )
    rows = await cursor.fetchall()
    history = [{"role": r[0], "content": r[1]} for r in reversed(rows)]

    context_block = format_portfolio_context(portfolio, watchlist)
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT + "\n\n" + context_block},
        *history,
        {"role": "user", "content": user_message},
    ]

    if os.environ.get("LLM_MOCK", "").lower() == "true":
        parsed = mock_response(user_message)
    else:
        api_key = os.environ.get("GOOGLE_API_KEY", "")
        try:
            response = await acompletion(
                model="gemini/gemini-3.1-flash-lite-preview",
                messages=messages,
                response_format=ChatResponse,
                api_key=api_key,
            )
            parsed = ChatResponse.model_validate_json(
                response.choices[0].message.content
            )
        except Exception as exc:
            log.exception("LLM call failed")
            parsed = ChatResponse(
                message=f"Sorry, I encountered an error processing your request: {exc}"
            )

    # Auto-execute trades
    errors: list[str] = []
    executed_trades: list[dict] = []
    for trade in parsed.trades:
        result, error = await execute_trade(
            price_cache, trade.ticker.upper(), trade.side, trade.quantity
        )
        if error:
            errors.append(
                f"Trade failed ({trade.side} {trade.quantity} {trade.ticker}): {error}"
            )
        else:
            executed_trades.append(result["trade"])

    # Auto-execute watchlist changes
    executed_watchlist: list[dict] = []
    for change in parsed.watchlist_changes:
        try:
            if change.action == "add":
                await add_ticker(change.ticker, price_cache, data_source)
                executed_watchlist.append(
                    {"ticker": change.ticker.upper(), "action": "add"}
                )
            elif change.action == "remove":
                await remove_ticker(change.ticker, data_source)
                executed_watchlist.append(
                    {"ticker": change.ticker.upper(), "action": "remove"}
                )
        except Exception as exc:
            errors.append(
                f"Watchlist {change.action} {change.ticker} failed: {exc}"
            )

    # Append errors to message
    final_message = parsed.message
    if errors:
        final_message += "\n\n" + "\n".join(errors)

    # Store messages in DB
    now = datetime.now(timezone.utc).isoformat()
    actions_json = (
        json.dumps(
            {
                "trades": executed_trades,
                "watchlist_changes": executed_watchlist,
            }
        )
        if (executed_trades or executed_watchlist)
        else None
    )

    await db.execute(
        "INSERT INTO chat_messages (id, user_id, role, content, actions, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (str(uuid.uuid4()), "default", "user", user_message, None, now),
    )
    await db.execute(
        "INSERT INTO chat_messages (id, user_id, role, content, actions, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (str(uuid.uuid4()), "default", "assistant", final_message, actions_json, now),
    )
    await db.commit()

    return {
        "message": final_message,
        "actions": {
            "trades": executed_trades,
            "watchlist_changes": executed_watchlist,
        },
    }
