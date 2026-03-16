"""Database subsystem for FinAlly.

Public API:
    get_db          - Lazy singleton connection (creates schema + seeds on first call)
    close_db        - Close connection and reset singleton
    init_schema     - Create all tables (used internally and in tests)
    seed_defaults   - Seed default user and watchlist (idempotent)
    DEFAULT_TICKERS - List of 10 default watchlist tickers
"""

from .connection import close_db, get_db
from .schema import init_schema
from .seed import DEFAULT_TICKERS, seed_defaults

__all__ = [
    "get_db",
    "close_db",
    "init_schema",
    "seed_defaults",
    "DEFAULT_TICKERS",
]
