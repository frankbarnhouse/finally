"""HTTP-level tests for chat API endpoint."""

from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.db import get_db, close_db
from app.market import PriceCache, MarketDataSource
from app.api.chat import create_chat_router


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
    return AsyncMock(spec=MarketDataSource)


@pytest.fixture
def app(db, price_cache, data_source, monkeypatch):
    monkeypatch.setenv("LLM_MOCK", "true")
    app = FastAPI()
    app.include_router(create_chat_router(price_cache, data_source))
    return app


@pytest.fixture
async def client(app):
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c


async def test_chat_endpoint_returns_response(client):
    """POST /api/chat with a simple message returns 200 with message and actions keys."""
    resp = await client.post("/api/chat", json={"message": "hello"})
    assert resp.status_code == 200
    data = resp.json()
    assert "message" in data
    assert "actions" in data


async def test_chat_endpoint_mock_buy(client):
    """POST /api/chat with buy message returns 200 with trade action in mock mode."""
    resp = await client.post("/api/chat", json={"message": "buy AAPL"})
    assert resp.status_code == 200
    data = resp.json()
    assert "message" in data
    assert "actions" in data
    assert len(data["actions"]["trades"]) > 0


async def test_chat_endpoint_missing_message(client):
    """POST /api/chat with empty body returns 422 (Pydantic validation)."""
    resp = await client.post("/api/chat", json={})
    assert resp.status_code == 422


async def test_chat_endpoint_empty_message(client):
    """POST /api/chat with empty string message returns 200 (valid request)."""
    resp = await client.post("/api/chat", json={"message": ""})
    assert resp.status_code == 200
    data = resp.json()
    assert "message" in data
