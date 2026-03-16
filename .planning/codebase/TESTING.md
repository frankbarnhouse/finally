# Testing Patterns

**Analysis Date:** 2026-03-16

## Test Framework

**Runner:**
- `pytest` 8.3+ with `pytest-asyncio` 0.24+
- Config: `backend/pyproject.toml` under `[tool.pytest.ini_options]`

**Coverage:**
- `pytest-cov` 5.0+
- Source: `app/` directory only
- Config: `backend/pyproject.toml` under `[tool.coverage.run]` and `[tool.coverage.report]`

**Run Commands:**
```bash
cd backend
uv run --extra dev pytest -v              # All tests with verbose output
uv run --extra dev pytest --cov=app       # All tests with coverage report
uv run --extra dev pytest tests/market/test_cache.py  # Single file
uv run --extra dev ruff check app/ tests/ # Lint before tests
```

## Test File Organization

**Location:**
- Tests are in a separate `backend/tests/` tree, mirroring the `backend/app/` structure
- `tests/market/` mirrors `app/market/`
- Each module has one or more dedicated test files

**Naming:**
- Test files: `test_{module}.py` — `test_cache.py`, `test_models.py`, `test_simulator.py`
- When a module has both sync and async tests that serve different purposes, split by concern: `test_simulator.py` (GBMSimulator unit) vs `test_simulator_source.py` (SimulatorDataSource async integration)

**Structure:**
```
backend/
├── app/
│   └── market/
│       ├── cache.py
│       ├── factory.py
│       ├── massive_client.py
│       ├── models.py
│       ├── simulator.py
│       └── stream.py
└── tests/
    ├── conftest.py           # (currently empty placeholder)
    └── market/
        ├── test_cache.py
        ├── test_factory.py
        ├── test_massive.py
        ├── test_models.py
        ├── test_simulator.py
        └── test_simulator_source.py
```

## Test Structure

**Suite Organization:**
- One class per module under test, named `Test{ClassName}` or `Test{ModuleName}`
- Each test method covers exactly one behavior and is named to describe it

```python
class TestPriceCache:
    """Unit tests for the PriceCache."""

    def test_update_and_get(self):
        """Test updating and getting a price."""
        cache = PriceCache()
        update = cache.update("AAPL", 190.50)
        assert update.ticker == "AAPL"
        assert update.price == 190.50
        assert cache.get("AAPL") == update
```

**Async test class pattern:**
```python
@pytest.mark.asyncio
class TestSimulatorDataSource:
    """Integration tests for the SimulatorDataSource."""

    async def test_start_populates_cache(self):
        cache = PriceCache()
        source = SimulatorDataSource(price_cache=cache, update_interval=0.1)
        await source.start(["AAPL", "GOOGL"])
        assert cache.get("AAPL") is not None
        await source.stop()
```

**Key patterns:**
- `asyncio_mode = "auto"` in pyproject.toml — no need for `@pytest.mark.asyncio` on individual methods, only on the class
- Every async test starts its resource and always calls `await source.stop()` at the end — no fixture teardown, teardown is inline
- No `setUp`/`tearDown` — each test is fully self-contained, constructing its own objects

## Mocking

**Framework:** `unittest.mock` from the standard library — `MagicMock`, `patch`, `patch.dict`, `patch.object`

**Environment variable mocking:**
```python
import os
from unittest.mock import patch

def test_creates_simulator_when_no_api_key(self):
    with patch.dict(os.environ, {}, clear=True):
        source = create_market_data_source(cache)
    assert isinstance(source, SimulatorDataSource)
```

**Method patching (internal method injection):**
```python
with patch.object(source, "_fetch_snapshots", return_value=mock_snapshots):
    await source._poll_once()
```

**Side effect injection (error testing):**
```python
with patch.object(source, "_fetch_snapshots", side_effect=Exception("network error")):
    await source._poll_once()  # Should not raise
```

**External class patching:**
```python
with patch("app.market.massive_client.RESTClient"):
    await source.start(["AAPL"])
```

**What to mock:**
- External API clients (`RESTClient` from the `massive` library)
- Internal methods that make external calls (`_fetch_snapshots`)
- Environment variables (`os.environ`) using `patch.dict` with `clear=True`
- One-shot error injection into hot-path methods to test resilience

**What NOT to mock:**
- `PriceCache` — always use a real instance; it has no side effects
- `GBMSimulator` — unit test it directly; mock only when testing `SimulatorDataSource` resilience
- Standard library async primitives (`asyncio.sleep`, `asyncio.Task`) — use real timing with short intervals instead

## Fixtures

**conftest.py:** Currently a placeholder (`backend/tests/conftest.py` is empty). No shared fixtures exist yet.

**Test data construction:** Inline helper functions at module level (not pytest fixtures) when reusable:
```python
def _make_snapshot(ticker: str, price: float, timestamp_ms: int) -> MagicMock:
    """Create a mock Massive snapshot object."""
    snap = MagicMock()
    snap.ticker = ticker
    snap.last_trade = MagicMock()
    snap.last_trade.price = price
    snap.last_trade.timestamp = timestamp_ms
    return snap
```

**No factories or fixture files:** Test data is constructed inline per test or via module-level helper functions. No pytest fixtures for object creation.

## Coverage

**Configuration (`backend/pyproject.toml`):**
```toml
[tool.coverage.run]
source = ["app"]
omit = ["tests/*"]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise AssertionError",
    "raise NotImplementedError",
    "if __name__ == .__main__.:",
    "if TYPE_CHECKING:",
]
```

**Requirements:** No enforced minimum coverage threshold. Run with:
```bash
uv run --extra dev pytest --cov=app
```

## Test Types

**Unit Tests (`tests/market/test_cache.py`, `test_models.py`, `test_simulator.py`, `test_factory.py`):**
- Test a single class in isolation
- Synchronous (no `asyncio`) unless testing an `async def` method
- Direct object construction — no mocking of internal collaborators
- Fast — no I/O, no sleep

**Integration Tests (`tests/market/test_simulator_source.py`, `test_massive.py`):**
- Test async lifecycle: `start()` → operations → `stop()`
- Use real `PriceCache` instances
- Mock external I/O only (`_fetch_snapshots`, `RESTClient`)
- Use short real `asyncio.sleep()` intervals (0.05–0.3 seconds) to test timing-dependent behavior

**E2E Tests (`test/` directory):**
- Playwright-based browser tests
- Infrastructure: `docker-compose.test.yml` in `test/`
- Run against the full Docker container
- Use `LLM_MOCK=true` environment variable for deterministic AI responses
- Not yet implemented (directory contains only `node_modules`)

## Common Patterns

**Resilience testing (verify loop survives errors):**
```python
async def test_exception_resilience(self):
    call_count = 0
    original_step = GBMSimulator.step

    def step_with_one_error(self):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise RuntimeError("injected error for resilience test")
        return original_step(self)

    with patch.object(GBMSimulator, "step", step_with_one_error):
        await asyncio.sleep(0.25)

    assert source._task is not None
    assert not source._task.done()
```

**Immutability testing:**
```python
def test_immutability(self):
    update = PriceUpdate(ticker="AAPL", price=190.50, previous_price=190.00, timestamp=1234567890.0)
    with pytest.raises(AttributeError):
        update.price = 200.00
```

**No-op / idempotency testing:**
```python
def test_remove_nonexistent(self):
    cache = PriceCache()
    cache.remove("AAPL")  # Should not raise

async def test_stop_is_idempotent(self):
    await source.stop()
    await source.stop()  # Should not raise
```

**Edge case: zero/empty inputs:**
```python
def test_empty_step(self):
    sim = GBMSimulator(tickers=[])
    result = sim.step()
    assert result == {}
```

**Timing-based assertions (prefer version/counter over sleep assertions):**
```python
initial_version = cache.version
await asyncio.sleep(0.3)
assert cache.version > initial_version  # Prefer version counter over direct price comparison
```

---

*Testing analysis: 2026-03-16*
