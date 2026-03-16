"""Tests for the portfolio endpoints."""

import pytest


@pytest.mark.asyncio
async def test_get_portfolio_initial(client):
    resp = await client.get("/api/portfolio")
    assert resp.status_code == 200
    data = resp.json()
    assert data["cash_balance"] == 10000.0
    assert data["positions"] == []
    assert data["total_value"] == 10000.0
    assert data["unrealized_pnl"] == 0.0


@pytest.mark.asyncio
async def test_buy_stock(client):
    resp = await client.post(
        "/api/portfolio/trade",
        json={"ticker": "AAPL", "quantity": 10, "side": "buy"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["trade"]["ticker"] == "AAPL"
    assert data["trade"]["side"] == "buy"
    assert data["trade"]["quantity"] == 10
    assert data["trade"]["price"] == 190.00
    assert data["cash_balance"] == 8100.00
    assert data["position"]["ticker"] == "AAPL"
    assert data["position"]["quantity"] == 10
    assert data["position"]["avg_cost"] == 190.00


@pytest.mark.asyncio
async def test_sell_stock(client):
    # Buy first
    await client.post(
        "/api/portfolio/trade",
        json={"ticker": "AAPL", "quantity": 10, "side": "buy"},
    )
    # Sell half
    resp = await client.post(
        "/api/portfolio/trade",
        json={"ticker": "AAPL", "quantity": 5, "side": "sell"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["trade"]["side"] == "sell"
    assert data["trade"]["quantity"] == 5
    assert data["position"]["quantity"] == 5
    assert data["cash_balance"] == 9050.00  # 8100 + 5*190


@pytest.mark.asyncio
async def test_sell_closes_position(client):
    # Buy then sell all
    await client.post(
        "/api/portfolio/trade",
        json={"ticker": "AAPL", "quantity": 10, "side": "buy"},
    )
    resp = await client.post(
        "/api/portfolio/trade",
        json={"ticker": "AAPL", "quantity": 10, "side": "sell"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["position"] is None
    assert data["cash_balance"] == 10000.00


@pytest.mark.asyncio
async def test_buy_insufficient_cash(client):
    resp = await client.post(
        "/api/portfolio/trade",
        json={"ticker": "MSFT", "quantity": 100, "side": "buy"},
    )
    assert resp.status_code == 400
    assert "Insufficient cash" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_sell_no_position(client):
    resp = await client.post(
        "/api/portfolio/trade",
        json={"ticker": "AAPL", "quantity": 10, "side": "sell"},
    )
    assert resp.status_code == 400
    assert "No position" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_sell_insufficient_shares(client):
    await client.post(
        "/api/portfolio/trade",
        json={"ticker": "AAPL", "quantity": 5, "side": "buy"},
    )
    resp = await client.post(
        "/api/portfolio/trade",
        json={"ticker": "AAPL", "quantity": 10, "side": "sell"},
    )
    assert resp.status_code == 400
    assert "Insufficient shares" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_invalid_side(client):
    resp = await client.post(
        "/api/portfolio/trade",
        json={"ticker": "AAPL", "quantity": 10, "side": "short"},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_invalid_quantity(client):
    resp = await client.post(
        "/api/portfolio/trade",
        json={"ticker": "AAPL", "quantity": 0, "side": "buy"},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_no_price_available(client):
    resp = await client.post(
        "/api/portfolio/trade",
        json={"ticker": "ZZZZ", "quantity": 1, "side": "buy"},
    )
    assert resp.status_code == 400
    assert "No price available" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_buy_adds_to_existing_position(client):
    # Buy 5 at 190
    await client.post(
        "/api/portfolio/trade",
        json={"ticker": "AAPL", "quantity": 5, "side": "buy"},
    )
    # Buy 5 more (still at 190 since cache is static)
    resp = await client.post(
        "/api/portfolio/trade",
        json={"ticker": "AAPL", "quantity": 5, "side": "buy"},
    )
    data = resp.json()
    assert data["position"]["quantity"] == 10
    assert data["position"]["avg_cost"] == 190.00


@pytest.mark.asyncio
async def test_portfolio_history_empty(client):
    resp = await client.get("/api/portfolio/history")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_portfolio_history_after_trade(client):
    # Execute a trade to trigger snapshot
    await client.post(
        "/api/portfolio/trade",
        json={"ticker": "AAPL", "quantity": 10, "side": "buy"},
    )
    resp = await client.get("/api/portfolio/history")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert "total_value" in data[0]
    assert "recorded_at" in data[0]


@pytest.mark.asyncio
async def test_portfolio_with_position(client):
    await client.post(
        "/api/portfolio/trade",
        json={"ticker": "AAPL", "quantity": 10, "side": "buy"},
    )
    resp = await client.get("/api/portfolio")
    data = resp.json()
    assert len(data["positions"]) == 1
    pos = data["positions"][0]
    assert pos["ticker"] == "AAPL"
    assert pos["quantity"] == 10
    assert pos["current_price"] == 190.00
    assert pos["unrealized_pnl"] == 0.0  # bought at same price
