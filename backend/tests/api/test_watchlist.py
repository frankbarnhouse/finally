"""Tests for watchlist API endpoints."""

from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.db import get_db, close_db
from app.market import PriceCache, MarketDataSource
from app.api.watchlist import create_watchlist_router


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
    cache = PriceCache()
    cache.update("AAPL", 190.50)
    cache.update("GOOGL", 175.00)
    return cache


@pytest.fixture
def data_source():
    source = AsyncMock(spec=MarketDataSource)
    return source


@pytest.fixture
def app(db, price_cache, data_source):
    app = FastAPI()
    app.include_router(create_watchlist_router(price_cache, data_source))
    return app


@pytest.fixture
async def client(app):
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c


async def test_get_watchlist(client):
    resp = await client.get("/api/watchlist")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 10
    assert all("ticker" in item and "price" in item for item in data)


async def test_get_watchlist_with_prices(client):
    resp = await client.get("/api/watchlist")
    data = resp.json()
    aapl = next(item for item in data if item["ticker"] == "AAPL")
    assert aapl["price"] == 190.50


async def test_get_watchlist_no_price(client):
    resp = await client.get("/api/watchlist")
    data = resp.json()
    # JPM is in default watchlist but not in price_cache fixture
    jpm = next(item for item in data if item["ticker"] == "JPM")
    assert jpm["price"] is None


async def test_add_ticker(client):
    resp = await client.post("/api/watchlist", json={"ticker": "PYPL"})
    assert resp.status_code == 200
    assert resp.json()["ticker"] == "PYPL"

    resp = await client.get("/api/watchlist")
    tickers = [item["ticker"] for item in resp.json()]
    assert "PYPL" in tickers


async def test_add_ticker_uppercase(client):
    resp = await client.post("/api/watchlist", json={"ticker": "pypl"})
    assert resp.status_code == 200
    assert resp.json()["ticker"] == "PYPL"


async def test_add_duplicate_ticker(client):
    resp = await client.post("/api/watchlist", json={"ticker": "AAPL"})
    assert resp.status_code == 200


async def test_remove_ticker(client):
    resp = await client.delete("/api/watchlist/NFLX")
    assert resp.status_code == 200

    resp = await client.get("/api/watchlist")
    tickers = [item["ticker"] for item in resp.json()]
    assert "NFLX" not in tickers


async def test_remove_ticker_not_in_watchlist(client):
    resp = await client.delete("/api/watchlist/UNKNOWN")
    assert resp.status_code == 200


async def test_remove_ticker_with_position_keeps_tracking(client, db, data_source):
    """If user holds a position, removing from watchlist should NOT call data_source.remove_ticker."""
    await db.execute(
        "INSERT INTO positions (user_id, ticker, quantity, avg_cost, updated_at) VALUES (?, ?, ?, ?, ?)",
        ("default", "NFLX", 10, 500.0, "2026-01-01T00:00:00Z"),
    )
    await db.commit()

    resp = await client.delete("/api/watchlist/NFLX")
    assert resp.status_code == 200

    data_source.remove_ticker.assert_not_called()
