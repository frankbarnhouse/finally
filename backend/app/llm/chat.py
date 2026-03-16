"""Core chat handler: orchestrates LLM calls, trade execution, and message storage."""

from __future__ import annotations

import json
import os

import litellm

from app.db import (
    add_to_watchlist,
    get_chat_messages,
    get_positions,
    get_user_profile,
    get_watchlist,
    insert_chat_message,
    remove_from_watchlist,
)
from app.db.connection import Database
from app.market.cache import PriceCache

from .mock import mock_chat_response
from .prompts import build_system_prompt, format_portfolio_context

MODEL = "gemini/gemini-3.1-flash-lite-preview"


async def handle_chat_message(
    user_message: str,
    db: Database,
    price_cache: PriceCache,
    execute_trade_fn,
) -> dict:
    """Process a user chat message end-to-end.

    Args:
        user_message: The user's text message.
        db: Database instance.
        price_cache: Live price cache.
        execute_trade_fn: Async callable(db, ticker, side, quantity, price_cache) -> dict.
            Should return the trade result dict or raise ValueError on failure.
    """
    # Store user message
    await insert_chat_message(db, role="user", content=user_message)

    # Get LLM response (mock or real)
    if os.environ.get("LLM_MOCK", "").lower() == "true":
        llm_response = mock_chat_response(user_message)
    else:
        llm_response = await _call_llm(user_message, db, price_cache)

    # Auto-execute trades
    executed_trades = []
    for trade in llm_response.get("trades", []):
        try:
            result = await execute_trade_fn(
                db, trade["ticker"], trade["side"], trade["quantity"], price_cache
            )
            executed_trades.append(result)
        except (ValueError, KeyError) as e:
            llm_response["message"] += f"\n\nTrade failed: {e}"

    # Auto-execute watchlist changes
    executed_watchlist = []
    for change in llm_response.get("watchlist_changes", []):
        ticker = change["ticker"].upper()
        action = change["action"]
        if action == "add":
            await add_to_watchlist(db, ticker)
            executed_watchlist.append({"ticker": ticker, "action": "add"})
        elif action == "remove":
            await remove_from_watchlist(db, ticker)
            executed_watchlist.append({"ticker": ticker, "action": "remove"})

    # Build actions JSON for storage
    actions = None
    if executed_trades or executed_watchlist:
        actions = json.dumps({
            "trades": executed_trades,
            "watchlist_changes": executed_watchlist,
        })

    # Store assistant message
    await insert_chat_message(
        db, role="assistant", content=llm_response["message"], actions=actions
    )

    return {
        "message": llm_response["message"],
        "trades": executed_trades,
        "watchlist_changes": executed_watchlist,
    }


async def _call_llm(user_message: str, db: Database, price_cache: PriceCache) -> dict:
    """Call the LLM via LiteLLM and parse structured output."""
    # Build portfolio context
    profile = await get_user_profile(db)
    cash = profile["cash_balance"] if profile else 10000.0
    positions = await get_positions(db)
    watchlist_rows = await get_watchlist(db)

    # Enrich positions with current prices
    enriched_positions = []
    total_positions_value = 0.0
    for p in positions:
        current_price = price_cache.get_price(p["ticker"]) or p["avg_cost"]
        enriched_positions.append({
            "ticker": p["ticker"],
            "quantity": p["quantity"],
            "avg_cost": p["avg_cost"],
            "current_price": current_price,
        })
        total_positions_value += current_price * p["quantity"]

    # Enrich watchlist with current prices
    enriched_watchlist = []
    for w in watchlist_rows:
        price = price_cache.get_price(w["ticker"])
        enriched_watchlist.append({
            "ticker": w["ticker"],
            "price": price,
        })

    total_value = cash + total_positions_value
    context = format_portfolio_context(cash, enriched_positions, enriched_watchlist, total_value)
    system_prompt = build_system_prompt(context)

    # Load conversation history
    history = await get_chat_messages(db, limit=10)
    messages = [{"role": "system", "content": system_prompt}]
    for msg in history:
        messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": user_message})

    # Call LLM
    response = await litellm.acompletion(
        model=MODEL,
        messages=messages,
        response_format={"type": "json_object"},
        temperature=0.7,
    )

    raw = response.choices[0].message.content
    return _parse_llm_response(raw)


def _parse_llm_response(raw: str) -> dict:
    """Parse and validate the LLM's JSON response."""
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {
            "message": raw or "I had trouble formatting my response. Please try again.",
            "trades": [],
            "watchlist_changes": [],
        }

    # Ensure required fields
    result = {
        "message": data.get("message", ""),
        "trades": [],
        "watchlist_changes": [],
    }

    # Validate trades
    for t in data.get("trades", []):
        if (
            isinstance(t, dict)
            and "ticker" in t
            and "side" in t
            and "quantity" in t
            and t["side"] in ("buy", "sell")
            and isinstance(t["quantity"], (int, float))
            and t["quantity"] > 0
        ):
            result["trades"].append({
                "ticker": t["ticker"].upper(),
                "side": t["side"],
                "quantity": t["quantity"],
            })

    # Validate watchlist changes
    for w in data.get("watchlist_changes", []):
        if (
            isinstance(w, dict)
            and "ticker" in w
            and "action" in w
            and w["action"] in ("add", "remove")
        ):
            result["watchlist_changes"].append({
                "ticker": w["ticker"].upper(),
                "action": w["action"],
            })

    return result
