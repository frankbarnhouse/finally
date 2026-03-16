"""Tests for health check endpoint."""

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.health import create_health_router


@pytest.fixture
def app():
    app = FastAPI()
    app.include_router(create_health_router())
    return app


async def test_health_returns_ok(app):
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
