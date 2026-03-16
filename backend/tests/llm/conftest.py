"""Fixtures for LLM tests."""

import pytest

from app.db.connection import Database
from app.market.cache import PriceCache


@pytest.fixture
async def db(tmp_path):
    """Provide a fresh database for each test."""
    database = Database(path=str(tmp_path / "test.db"))
    await database.connect()
    yield database
    await database.close()


@pytest.fixture
def price_cache():
    """Provide a price cache with some default prices."""
    cache = PriceCache()
    cache.update("AAPL", 190.50)
    cache.update("GOOGL", 175.00)
    cache.update("MSFT", 420.00)
    cache.update("TSLA", 250.00)
    return cache
