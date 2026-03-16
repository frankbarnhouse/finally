"""HTTP-level tests for portfolio API endpoints."""

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.db import get_db, close_db
from app.api.portfolio import create_portfolio_router


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
    return MockPriceCache({"AAPL": 190.50, "GOOGL": 175.00})


@pytest.fixture
def app(price_cache):
    app = FastAPI()
    app.include_router(create_portfolio_router(price_cache))
    return app


@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def test_get_portfolio_returns_200(db, client):
    """GET /api/portfolio returns 200 with expected keys."""
    resp = await client.get("/api/portfolio")
    assert resp.status_code == 200
    data = resp.json()
    assert "positions" in data
    assert "cash_balance" in data
    assert "total_value" in data
    assert data["cash_balance"] == 10000.0


async def test_buy_trade_returns_200(db, client):
    """POST /api/portfolio/trade with valid buy returns trade result."""
    resp = await client.post(
        "/api/portfolio/trade",
        json={"ticker": "AAPL", "quantity": 5, "side": "buy"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "trade" in data
    assert "cash_balance" in data
    assert "position" in data
    assert data["trade"]["ticker"] == "AAPL"
    assert data["trade"]["side"] == "buy"


async def test_buy_insufficient_cash_returns_400(db, client):
    """POST /api/portfolio/trade with insufficient cash returns 400."""
    # Buy a huge amount to exceed $10k
    resp = await client.post(
        "/api/portfolio/trade",
        json={"ticker": "AAPL", "quantity": 1000, "side": "buy"},
    )
    assert resp.status_code == 400
    data = resp.json()
    assert "error" in data
    assert "Insufficient cash" in data["error"]


async def test_quantity_zero_returns_422(db, client):
    """POST /api/portfolio/trade with quantity=0 returns 422 (Pydantic validation)."""
    resp = await client.post(
        "/api/portfolio/trade",
        json={"ticker": "AAPL", "quantity": 0, "side": "buy"},
    )
    assert resp.status_code == 422


async def test_sell_closes_position_returns_null(db, client):
    """Selling entire position returns position: null."""
    # First buy
    await client.post(
        "/api/portfolio/trade",
        json={"ticker": "AAPL", "quantity": 10, "side": "buy"},
    )
    # Then sell all
    resp = await client.post(
        "/api/portfolio/trade",
        json={"ticker": "AAPL", "quantity": 10, "side": "sell"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["position"] is None


async def test_ticker_uppercased(db, client):
    """Ticker is uppercased by the endpoint."""
    resp = await client.post(
        "/api/portfolio/trade",
        json={"ticker": "aapl", "quantity": 1, "side": "buy"},
    )
    assert resp.status_code == 200
    assert resp.json()["trade"]["ticker"] == "AAPL"


async def test_get_portfolio_history_returns_200(db, client):
    """GET /api/portfolio/history returns 200 with list of snapshots."""
    import uuid

    # Insert a snapshot directly
    await db.execute(
        "INSERT INTO portfolio_snapshots (id, user_id, total_value, recorded_at) VALUES (?, ?, ?, ?)",
        (str(uuid.uuid4()), "default", 10000.0, "2026-01-01T00:00:00"),
    )
    await db.commit()

    resp = await client.get("/api/portfolio/history")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["total_value"] == 10000.0
    assert "recorded_at" in data[0]


async def test_trade_triggers_snapshot_via_api(db, client):
    """POST trade, then verify snapshot was recorded."""
    resp = await client.post(
        "/api/portfolio/trade",
        json={"ticker": "AAPL", "quantity": 5, "side": "buy"},
    )
    assert resp.status_code == 200

    cursor = await db.execute(
        "SELECT COUNT(*) FROM portfolio_snapshots WHERE user_id = 'default'"
    )
    row = await cursor.fetchone()
    assert row[0] >= 1
