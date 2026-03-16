"""Tests for CRUD query functions."""

import json

from app.db import queries


async def test_get_user_profile(db):
    profile = await queries.get_user_profile(db)
    assert profile is not None
    assert profile["id"] == "default"
    assert profile["cash_balance"] == 10000.0


async def test_update_cash_balance(db):
    await queries.update_cash_balance(db, 5000.0)
    profile = await queries.get_user_profile(db)
    assert profile["cash_balance"] == 5000.0


# --- Watchlist ---

async def test_get_watchlist(db):
    wl = await queries.get_watchlist(db)
    assert len(wl) == 10
    assert wl[0]["ticker"] == "AAPL"


async def test_add_to_watchlist(db):
    result = await queries.add_to_watchlist(db, "PYPL")
    assert result["ticker"] == "PYPL"
    wl = await queries.get_watchlist(db)
    assert len(wl) == 11


async def test_add_duplicate_watchlist(db):
    await queries.add_to_watchlist(db, "AAPL")
    wl = await queries.get_watchlist(db)
    assert len(wl) == 10  # no duplicate


async def test_remove_from_watchlist(db):
    removed = await queries.remove_from_watchlist(db, "AAPL")
    assert removed is True
    wl = await queries.get_watchlist(db)
    assert len(wl) == 9


async def test_remove_nonexistent_watchlist(db):
    removed = await queries.remove_from_watchlist(db, "ZZZZ")
    assert removed is False


# --- Positions ---

async def test_upsert_and_get_position(db):
    await queries.upsert_position(db, "AAPL", 10.0, 190.50)
    pos = await queries.get_position(db, "AAPL")
    assert pos is not None
    assert pos["quantity"] == 10.0
    assert pos["avg_cost"] == 190.50


async def test_upsert_updates_existing(db):
    await queries.upsert_position(db, "AAPL", 10.0, 190.50)
    await queries.upsert_position(db, "AAPL", 20.0, 185.25)
    pos = await queries.get_position(db, "AAPL")
    assert pos["quantity"] == 20.0
    assert pos["avg_cost"] == 185.25


async def test_get_positions_empty(db):
    positions = await queries.get_positions(db)
    assert positions == []


async def test_delete_position(db):
    await queries.upsert_position(db, "AAPL", 10.0, 190.50)
    deleted = await queries.delete_position(db, "AAPL")
    assert deleted is True
    pos = await queries.get_position(db, "AAPL")
    assert pos is None


async def test_delete_nonexistent_position(db):
    deleted = await queries.delete_position(db, "ZZZZ")
    assert deleted is False


# --- Trades ---

async def test_insert_and_get_trades(db):
    trade = await queries.insert_trade(db, "AAPL", "buy", 10.0, 190.50)
    assert trade["ticker"] == "AAPL"
    assert trade["side"] == "buy"
    assert trade["quantity"] == 10.0

    trades = await queries.get_trades(db)
    assert len(trades) == 1
    assert trades[0]["id"] == trade["id"]


async def test_trades_ordered_desc(db):
    await queries.insert_trade(db, "AAPL", "buy", 5.0, 190.0)
    await queries.insert_trade(db, "GOOGL", "buy", 3.0, 175.0)
    trades = await queries.get_trades(db)
    assert trades[0]["ticker"] == "GOOGL"  # most recent first


# --- Portfolio Snapshots ---

async def test_insert_and_get_snapshots(db):
    snap = await queries.insert_snapshot(db, 10500.0)
    assert snap["total_value"] == 10500.0

    snaps = await queries.get_snapshots(db)
    assert len(snaps) == 1
    assert snaps[0]["id"] == snap["id"]


# --- Chat Messages ---

async def test_insert_and_get_chat_messages(db):
    msg = await queries.insert_chat_message(db, "user", "Hello")
    assert msg["role"] == "user"
    assert msg["content"] == "Hello"
    assert msg["actions"] is None

    messages = await queries.get_chat_messages(db)
    assert len(messages) == 1


async def test_chat_messages_with_actions(db):
    actions = json.dumps({"trades": [{"ticker": "AAPL", "side": "buy", "quantity": 10}]})
    msg = await queries.insert_chat_message(db, "assistant", "Done!", actions=actions)
    assert msg["actions"] == actions


async def test_chat_messages_ordered_chronologically(db):
    await queries.insert_chat_message(db, "user", "First")
    await queries.insert_chat_message(db, "assistant", "Second")
    messages = await queries.get_chat_messages(db)
    assert messages[0]["content"] == "First"
    assert messages[1]["content"] == "Second"


async def test_chat_messages_limit(db):
    for i in range(15):
        await queries.insert_chat_message(db, "user", f"Message {i}")
    messages = await queries.get_chat_messages(db, limit=10)
    assert len(messages) == 10
    # Should be the 10 most recent, in chronological order
    assert messages[0]["content"] == "Message 5"
    assert messages[9]["content"] == "Message 14"
