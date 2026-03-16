"""Fixtures for database tests."""

import pytest

from app.db.connection import Database


@pytest.fixture
async def db(tmp_path):
    """Provide a fresh in-memory-like database for each test."""
    database = Database(path=str(tmp_path / "test.db"))
    await database.connect()
    yield database
    await database.close()
