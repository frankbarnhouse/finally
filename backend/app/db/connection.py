"""Lazy singleton SQLite connection with WAL mode."""

from pathlib import Path

import aiosqlite

from .schema import init_schema
from .seed import seed_defaults

DB_PATH = Path("db/finally.db")

_db: aiosqlite.Connection | None = None


async def get_db() -> aiosqlite.Connection:
    """Return the singleton database connection, initializing on first call."""
    global _db
    if _db is None:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        _db = await aiosqlite.connect(str(DB_PATH))
        _db.row_factory = aiosqlite.Row
        await _db.execute("PRAGMA journal_mode=WAL")
        await _db.execute("PRAGMA busy_timeout=5000")
        await init_schema(_db)
        await seed_defaults(_db)
    return _db


async def close_db() -> None:
    """Close the database connection and reset the singleton."""
    global _db
    if _db is not None:
        await _db.close()
        _db = None
