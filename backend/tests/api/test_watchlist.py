"""Tests for the watchlist endpoints."""

import pytest


@pytest.mark.asyncio
async def test_list_watchlist(client):
    resp = await client.get("/api/watchlist")
    assert resp.status_code == 200
    data = resp.json()
    # Default seed has 10 tickers
    assert len(data) == 10
    tickers = [item["ticker"] for item in data]
    assert "AAPL" in tickers
    assert "GOOGL" in tickers


@pytest.mark.asyncio
async def test_list_watchlist_includes_prices(client):
    resp = await client.get("/api/watchlist")
    data = resp.json()
    aapl = next(item for item in data if item["ticker"] == "AAPL")
    # AAPL has a price in the test cache
    assert "price" in aapl
    assert aapl["price"] == 190.00


@pytest.mark.asyncio
async def test_add_ticker(client):
    resp = await client.post("/api/watchlist", json={"ticker": "PYPL"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["ticker"] == "PYPL"

    # Verify it appears in the list
    resp = await client.get("/api/watchlist")
    tickers = [item["ticker"] for item in resp.json()]
    assert "PYPL" in tickers


@pytest.mark.asyncio
async def test_add_duplicate_ticker(client):
    resp = await client.post("/api/watchlist", json={"ticker": "AAPL"})
    assert resp.status_code == 201
    # Should still only have 10 (not 11) since AAPL was already there
    resp = await client.get("/api/watchlist")
    tickers = [item["ticker"] for item in resp.json()]
    assert tickers.count("AAPL") == 1


@pytest.mark.asyncio
async def test_remove_ticker(client):
    resp = await client.delete("/api/watchlist/AAPL")
    assert resp.status_code == 200
    assert resp.json() == {"removed": "AAPL"}

    resp = await client.get("/api/watchlist")
    tickers = [item["ticker"] for item in resp.json()]
    assert "AAPL" not in tickers


@pytest.mark.asyncio
async def test_remove_nonexistent_ticker(client):
    resp = await client.delete("/api/watchlist/ZZZZ")
    assert resp.status_code == 404
