# Coding Conventions

**Analysis Date:** 2026-03-16

## Naming Patterns

**Files:**
- `snake_case.py` for all Python modules: `cache.py`, `massive_client.py`, `seed_prices.py`, `simulator.py`
- Module names are short and descriptive nouns or noun phrases
- Test files mirror the source module name with `test_` prefix: `test_cache.py`, `test_simulator.py`
- Integration tests for async sources use a separate file: `test_simulator_source.py` vs `test_simulator.py`

**Classes:**
- `PascalCase` for all classes: `PriceCache`, `GBMSimulator`, `SimulatorDataSource`, `MassiveDataSource`
- Abstract base class named as the interface contract (not `IFoo`): `MarketDataSource`
- Test classes prefixed with `Test`: `TestPriceCache`, `TestGBMSimulator`, `TestFactory`

**Functions and Methods:**
- `snake_case` for all functions and methods
- Public methods: plain verb or noun phrase — `update`, `get_all`, `get_price`, `add_ticker`, `remove_ticker`
- Private methods: single leading underscore — `_add_ticker_internal`, `_rebuild_cholesky`, `_poll_once`, `_run_loop`
- Factory functions: `create_` prefix — `create_market_data_source`, `create_stream_router`
- Test functions: `test_` prefix followed by what is being asserted — `test_direction_up`, `test_remove_nonexistent_is_noop`

**Variables:**
- `snake_case` for all locals and instance variables
- Private instance attributes: single leading underscore — `self._prices`, `self._lock`, `self._task`
- Module-level constants: `UPPER_SNAKE_CASE` — `SEED_PRICES`, `TICKER_PARAMS`, `DEFAULT_PARAMS`, `INTRA_TECH_CORR`
- Loop variables: short and clear — `ticker`, `price`, `snap`, `update`

**Types:**
- Type hints used throughout all public APIs and most private methods
- Use `from __future__ import annotations` at top of every module (deferred evaluation)
- Union types with `|` syntax (Python 3.10+ style): `PriceUpdate | None`, `asyncio.Task | None`
- Return types always annotated on public methods
- `dict`, `list` lowercase for generics (not `Dict`, `List`)

## Code Style

**Formatter/Linter:**
- `ruff` for both linting and formatting — configured in `backend/pyproject.toml`
- Line length: 100 characters (`line-length = 100`)
- Target version: Python 3.12 (`target-version = "py312"`)
- Active rule sets: `E` (pycodestyle errors), `F` (pyflakes), `I` (isort), `N` (pep8-naming), `W` (pycodestyle warnings)
- `E501` (line too long) is ignored — line length is handled by the formatter, not the linter

**Run linting:**
```bash
cd backend
uv run --extra dev ruff check app/ tests/
```

## Import Organization

**Order (enforced by ruff `I` rules):**
1. `from __future__ import annotations` (always first when present)
2. Standard library (`asyncio`, `logging`, `math`, `os`, `random`, `threading`, `time`)
3. Third-party (`fastapi`, `massive`, `numpy`)
4. Local relative imports (`.cache`, `.interface`, `.models`)

**Style:**
- Relative imports within a package: `from .cache import PriceCache`
- Absolute imports in tests: `from app.market.cache import PriceCache`
- No wildcard imports (`from x import *`)
- `__all__` used in `__init__.py` to declare the public API explicitly

## Docstrings

**Module docstrings:**
- Every module has a one-line module docstring: `"""Thread-safe in-memory price cache."""`

**Class docstrings:**
- Every class has a docstring describing its purpose and, where relevant, its lifecycle or threading model
- Multi-line docstrings include context about design decisions (e.g., who writes/reads the cache)

**Method docstrings:**
- Public methods always have a docstring
- Private methods have docstrings when the logic is non-obvious
- One-liners use a single line: `"""Convenience: get just the price float, or None."""`
- Multi-line docstrings document the behavior contract, not just what the method does

**Example pattern from `cache.py`:**
```python
def update(self, ticker: str, price: float, timestamp: float | None = None) -> PriceUpdate:
    """Record a new price for a ticker. Returns the created PriceUpdate.

    Automatically computes direction and change from the previous price.
    If this is the first update for the ticker, previous_price == price (direction='flat').
    """
```

## Comments

**Inline comments:**
- Used sparingly and only when the code alone is insufficient
- Explain the "why", not the "what": `# Monotonically increasing; bumped on every update`
- Mathematical formulas documented inline in the class docstring, not scattered in the method body

**Section dividers:**
- Used in longer classes to separate public API from internals: `# --- Public API ---`, `# --- Internals ---`

## Error Handling

**Pattern:** Let exceptions propagate unless recovery is meaningful.

**Background loop exception handling:**
- Catch broad `Exception` in background task loops to prevent task death
- Log with `logger.exception(...)` or `logger.error(...)` — never silently swallow
- Do NOT re-raise inside loops: `# Don't re-raise — the loop will retry on the next interval.`

**External API parsing:**
- Catch specific exceptions (`AttributeError`, `TypeError`) when iterating over untrusted data
- Log malformed items as warnings and continue: `logger.warning("Skipping snapshot for %s: %s", ...)`

**No defensive programming for happy paths:**
- Methods like `remove` on non-existent keys use `dict.pop(key, None)` — no prior existence check
- No-op methods documented explicitly: `"""No-op if already present."""`

## Logging

**Framework:** Python standard library `logging`

**Setup pattern:**
```python
import logging
logger = logging.getLogger(__name__)
```

- One logger per module, named after the module
- `logger.info(...)` for lifecycle events: start, stop, ticker add/remove
- `logger.debug(...)` for hot-path details: per-tick events, poll counts
- `logger.warning(...)` for recoverable data issues: malformed API responses
- `logger.error(...)` for external failures: API poll errors
- `logger.exception(...)` inside `except` blocks to include stack trace
- Use `%s` style formatting (lazy), never f-strings in log calls

## Async Patterns

- All I/O-bound operations are `async def`
- Synchronous library calls that may block are run in a thread: `await asyncio.to_thread(self._fetch_snapshots)`
- Background tasks created with `asyncio.create_task(coro, name="descriptive-name")`
- Task cancellation pattern: cancel, then `await task` inside `try/except asyncio.CancelledError: pass`
- `asyncio_mode = "auto"` in pytest config — all async test methods run automatically

## Data Models

- Immutable value objects use `@dataclass(frozen=True, slots=True)`
- Computed properties use `@property` — no setter needed for immutable dataclasses
- Serialization method named `to_dict()` returning `dict`
- Default factory for mutable defaults: `field(default_factory=time.time)`

## Module Structure

**Exports:** Explicit `__all__` in `__init__.py` listing only public symbols.

**Public API surface:** Only what is listed in `__init__.py` is considered public. All implementation classes and helpers are importable but should be accessed via the package public API.

**Factory pattern:** Used instead of constructor overloading. `create_market_data_source(cache)` reads environment and returns the appropriate implementation — callers never import concrete classes directly.

---

*Convention analysis: 2026-03-16*
