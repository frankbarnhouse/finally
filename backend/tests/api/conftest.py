"""Fixtures for API tests."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.db.connection import Database
from app.market import PriceCache


@pytest.fixture
async def db(tmp_path):
    """Provide a fresh database for each test."""
    database = Database(path=str(tmp_path / "test.db"))
    await database.connect()
    yield database
    await database.close()


@pytest.fixture
def price_cache():
    """Provide a PriceCache with some test prices."""
    cache = PriceCache()
    cache.update("AAPL", 190.00)
    cache.update("GOOGL", 175.00)
    cache.update("MSFT", 420.00)
    cache.update("TSLA", 250.00)
    return cache


@pytest.fixture
async def client(tmp_path, monkeypatch):
    """Provide an async test client with a fresh DB and price cache."""
    import app.db.connection as conn_mod
    from app.api import portfolio as portfolio_mod
    from app.api import watchlist as watchlist_mod

    # Use a fresh database for each test
    db = Database(path=str(tmp_path / "test.db"))
    await db.connect()

    # Patch get_db to return our test db
    async def _get_db(path=None):
        return db

    monkeypatch.setattr(conn_mod, "_db", db)
    monkeypatch.setattr(conn_mod, "get_db", _get_db)

    # Set up price cache
    cache = PriceCache()
    cache.update("AAPL", 190.00)
    cache.update("GOOGL", 175.00)
    cache.update("MSFT", 420.00)
    cache.update("TSLA", 250.00)

    portfolio_mod.init_portfolio_router(cache)
    watchlist_mod.init_watchlist_router(cache, None)

    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    await db.close()
