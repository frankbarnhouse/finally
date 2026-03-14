# Market Data Backend — Code Review

**Reviewed:** 2026-03-14
**Reviewer:** Claude (claude-sonnet-4-6)
**Scope:** `backend/app/market/` and `backend/tests/market/`

---

## Executive Summary

The market data backend is **well-implemented and production-quality** for this demo application. The code is clean, well-structured, and closely follows the design specification. Test coverage is comprehensive. Three minor bugs and a few design observations were identified; none are blocking.

---

## Test Run Results

> **Note:** The CI sandbox environment restricts execution of `python3`, `uv`, and `pip` commands. Tests could not be run directly. This section reports a static analysis of the test suite against the implementation.

### Static Analysis — Expected Test Outcomes

| File | Tests | Expected Result |
|---|---|---|
| `test_models.py` | 9 | All pass |
| `test_cache.py` | 12 | All pass |
| `test_simulator.py` | 16 | All pass |
| `test_simulator_source.py` | 9 | All pass |
| `test_massive.py` | 13 | All pass |
| `test_factory.py` | 7 | All pass |
| **Total** | **66** | **All expected to pass** |

Each test was matched against its corresponding implementation. All assertions are consistent with the code. No test is expected to fail based on static analysis.

### Linting

Ruff configuration (`pyproject.toml`): rules `E`, `F`, `I`, `N`, `W` with `E501` (line-length) ignored. A manual review found no violations in any file in `app/market/`. All imports are sorted, no unused imports, naming conventions are consistent.

---

## Module-by-Module Review

### `models.py` — `PriceUpdate`

**Rating: Excellent**

- Clean frozen dataclass with `slots=True` for memory efficiency.
- `@property` implementations are correct: `change`, `change_percent`, `direction`.
- Zero-division guard in `change_percent` (`if self.previous_price == 0: return 0.0`) is correct.
- `to_dict()` computes all derived fields correctly for SSE serialization.
- `field(default_factory=time.time)` is the right pattern for a mutable default.

No issues found.

---

### `cache.py` — `PriceCache`

**Rating: Very Good**

- Thread-safe via `threading.Lock()`. All mutating methods acquire the lock.
- `get_all()` returns a shallow copy (`dict(self._prices)`) — correct, prevents external mutation of the internal dict.
- First update sets `previous_price = price` (direction `flat`) — correct behavior.
- Prices are rounded to 2 decimal places on write.

**Minor Issue — Unsynchronized version read (cosmetic):**

```python
@property
def version(self) -> int:
    return self._version  # No lock acquired
```

The `version` property reads `self._version` without holding the lock. In CPython, integer reads are effectively atomic due to the GIL, so this doesn't cause data corruption. However, a caller reading `version` then calling `get_all()` performs two separate atomic operations, creating a small TOCTOU window. In `stream.py`, this means an SSE client could theoretically send one extra update if the version changes between the two reads. The consequence is a harmless extra push to the client, not data corruption. Acceptable for this use case.

---

### `interface.py` — `MarketDataSource`

**Rating: Excellent**

Clean abstract base class. Lifecycle contract is clearly documented. The `stop()` is documented as safe to call multiple times, which both implementations honour correctly.

**Minor Design Note:** The docstring states "Calling `start()` twice is undefined behavior." Both implementations (`SimulatorDataSource`, `MassiveDataSource`) would silently start a second background task if called twice, leaking a runnable asyncio task. For a production system, a guard (`if self._task is not None: raise RuntimeError(...)`) would be appropriate. For this demo application, it's an acceptable risk since `start()` is called once from the FastAPI lifespan.

---

### `factory.py` — `create_market_data_source`

**Rating: Excellent**

- `.strip()` on the API key correctly handles whitespace-only values.
- Logging at `INFO` level on startup is helpful for operators.
- Factory function signature is clean and testable.

No issues found.

---

### `simulator.py` — `GBMSimulator` and `SimulatorDataSource`

**Rating: Excellent**

#### GBM Math Verification

The formula is correctly implemented:

```
S(t+dt) = S(t) * exp((mu - 0.5*sigma^2)*dt + sigma*sqrt(dt)*Z)
```

- The Itô correction term `(mu - 0.5*sigma^2)` is present — correct for log-normal GBM.
- `dt = 0.5 / (252 * 6.5 * 3600) ≈ 8.48e-8` is the correct value for 500ms ticks over a 252-day, 6.5h/day trading year.
- Cholesky decomposition of the correlation matrix correctly produces correlated normal draws: `z_correlated = L @ z_independent` where `L = cholesky(C)`.
- GBM prices are always positive (exp of real number is always positive) — confirmed by `test_prices_are_positive` which runs 10,000 steps.

#### Correlation Model

- Cholesky is set to `None` for ≤1 ticker (avoids unnecessary computation, handled correctly in `step()`).
- The correlation matrix is rebuilt on every `add_ticker()` / `remove_ticker()` — correct, since O(n²) with n<50 is instant.

**Observation — TSLA in tech group but special-cased:**

```python
CORRELATION_GROUPS = {
    "tech": {"AAPL", "GOOGL", "MSFT", "AMZN", "META", "NVDA", "NFLX"},  # TSLA not here
    "finance": {"JPM", "V"},
}
```

Wait — TSLA is actually *not* in the tech group in `seed_prices.py` (it is absent from the `tech` set). However, `_pairwise_correlation` still checks `if t1 == "TSLA" or t2 == "TSLA": return TSLA_CORR` first, which is consistent. No bug here — just worth confirming the TSLA/tech relationship is intentional (it is, per the design doc).

**Minor Issue — No input normalization in `SimulatorDataSource`:**

```python
async def add_ticker(self, ticker: str) -> None:
    if self._sim:
        self._sim.add_ticker(ticker)  # No .upper() or .strip()
```

If a caller passes `"aapl"` instead of `"AAPL"`, the simulator tracks a separate ticker with a random seed price (since `SEED_PRICES.get("aapl")` returns `None`). Compare with `MassiveDataSource` which does normalize. The upstream callers (watchlist API) should normalize before calling, but a defensive `.upper().strip()` here would be safer.

**Minor Issue — No guard for calling `add_ticker()` before `start()`:**

```python
async def add_ticker(self, ticker: str) -> None:
    if self._sim:  # Silently does nothing if not started
        ...
```

The `if self._sim:` guard silently discards tickers added before `start()` is called. This is fine for the current usage pattern (tickers are seeded via `start()`), but is a silent failure mode that could confuse future developers.

#### `SimulatorDataSource._run_loop`

```python
except Exception:
    logger.exception("Simulator step failed")
```

The broad exception handler is correct here — it prevents a transient numpy error from killing the background task. The loop continues after logging.

---

### `massive_client.py` — `MassiveDataSource`

**Rating: Very Good**

- `asyncio.to_thread(self._fetch_snapshots)` correctly offloads the synchronous `RESTClient` call without blocking the event loop.
- Milliseconds-to-seconds timestamp conversion (`/ 1000.0`) is correct.
- Per-snapshot error handling (AttributeError, TypeError) correctly skips malformed entries while processing the rest.
- API errors are logged and swallowed at the poll level — the loop retries on the next interval.

**Bug — Input normalization not applied in `start()`:**

```python
async def start(self, tickers: list[str]) -> None:
    self._client = RESTClient(api_key=self._api_key)
    self._tickers = list(tickers)  # No normalization
```

`add_ticker()` and `remove_ticker()` both call `.upper().strip()`, but `start()` stores tickers as-is. If tickers with lowercase or extra whitespace are passed to `start()`, they'll be stored differently than tickers added via `add_ticker()`, causing inconsistencies. For example, `start(["aapl"])` then `remove_ticker("AAPL")` would leave `"aapl"` in the list.

**Fix:** Add normalization at the top of `start()`:
```python
self._tickers = [t.upper().strip() for t in tickers]
```

---

### `stream.py` — SSE Streaming

**Rating: Good**

- `retry: 1000\n\n` directive correctly instructs browsers to reconnect after 1 second.
- `X-Accel-Buffering: no` header is a thoughtful production detail for nginx-proxied deployments.
- Disconnect detection via `await request.is_disconnected()` is the correct FastAPI pattern.
- `CancelledError` is caught and logged cleanly.

**Bug — Global router modified by factory function:**

```python
# Module level:
router = APIRouter(prefix="/api/stream", tags=["streaming"])

def create_stream_router(price_cache: PriceCache) -> APIRouter:
    @router.get("/prices")  # Registers on the global router
    async def stream_prices(request: Request) -> StreamingResponse:
        ...
    return router
```

`create_stream_router()` registers a route on the module-level `router` object and returns it. If called multiple times (e.g., in unit tests), the `/prices` route is registered multiple times on the same router, generating FastAPI duplicate-route warnings and unpredictable behavior.

**Fix:** Create a new router inside the factory:
```python
def create_stream_router(price_cache: PriceCache) -> APIRouter:
    router = APIRouter(prefix="/api/stream", tags=["streaming"])
    @router.get("/prices")
    ...
    return router
```

**Observation — Sends all ticker prices per update:**

The SSE endpoint sends all prices every interval, not just changed prices. With 10 tickers at 500ms, this is ~10 JSON objects per push, well within acceptable payload size. The version-change guard (`current_version != last_version`) avoids sending if nothing changed, which is good. This is an appropriate design for the demo scale.

---

### `seed_prices.py`

**Rating: Excellent**

Clean data file. Prices, volatility, and drift parameters are well-chosen and match the design spec. `DEFAULT_PARAMS` for unknown tickers (sigma=0.25, mu=0.05) are reasonable defaults. No issues.

---

### `__init__.py`

**Rating: Excellent**

Clean public API with `__all__` defined. Exports only what downstream code needs. No issues.

---

## Test Quality Assessment

### Strengths

- Good coverage of happy paths and edge cases.
- Error handling tests: malformed snapshots (`test_malformed_snapshot_skipped`), API failures (`test_api_error_does_not_crash`).
- Idempotency tests: double-stop, duplicate-add.
- Mathematical property tests: prices always positive (10,000 steps), prices change over time (1,000 steps).
- Correlation tests verify exact coefficients from `seed_prices.py`.
- Factory tests properly isolate environment via `patch.dict(os.environ, ..., clear=True)`.

### Weak Tests

**`test_exception_resilience` (misleading name):**
```python
async def test_exception_resilience(self):
    """Test that simulator continues running after errors."""
    await source.start(["AAPL"])
    await asyncio.sleep(0.15)
    assert source._task is not None
    assert not source._task.done()
```
This test doesn't actually inject an exception — it just verifies the task is still running after normal operation. A stronger version would monkeypatch `GBMSimulator.step` to raise on one call, then verify the task continues. The test still provides value (task liveness check) but doesn't test the exception handler.

**`test_custom_event_probability`:**
```python
async def test_custom_event_probability(self):
    source = SimulatorDataSource(..., event_probability=1.0)
    await source.start(["AAPL"])
    await asyncio.sleep(0.2)
    await source.stop()
```
With `event_probability=1.0`, every tick should produce a 2-5% shock. The test only verifies clean start/stop, not that events actually occur or that they don't break the math. A stronger test would verify that high-probability events still produce positive, bounded prices.

### Missing Tests

The following scenarios have no test coverage:

1. **`SimulatorDataSource.add_ticker()` called before `start()`** — currently silently discarded due to `if self._sim:`. No test documents this behavior.
2. **SSE `_generate_events` generator** — no tests for the streaming endpoint itself.
3. **`_pairwise_correlation` with two unknown tickers** — the cross-sector fallback path is tested indirectly (AAPL+JPM = 0.3), but unknown-unknown is not explicitly tested.
4. **Ticker normalization consistency** — no test verifying that the same ticker passed in different cases to `SimulatorDataSource` doesn't create duplicates.
5. **`PriceCache` thread-safety** — no concurrent write/read test (though the implementation is correct).

### `conftest.py` — Unused Fixture

```python
@pytest.fixture
def event_loop_policy():
    return asyncio.DefaultEventLoopPolicy()
```

This fixture is never used by any test and has no `autouse=True`. The `asyncio_mode = "auto"` setting in `pyproject.toml` handles async test collection. This is dead code.

---

## Summary of Issues

| # | Severity | File | Issue |
|---|---|---|---|
| 1 | **Bug** | `stream.py:20` | Global router mutated by factory; calling `create_stream_router()` twice registers duplicate routes |
| 2 | **Bug** | `massive_client.py:41` | `start()` doesn't normalize tickers with `.upper().strip()` like `add_ticker()`/`remove_ticker()` do |
| 3 | **Minor** | `simulator.py:242` | `add_ticker()` doesn't normalize case/whitespace; silent no-op if called before `start()` |
| 4 | **Minor** | `cache.py:65` | `version` property reads without lock (cosmetic — atomic in CPython, harmless for this use case) |
| 5 | **Minor** | `interface.py:26` | `start()` called twice is undefined behavior; no guard against double-start |
| 6 | **Cosmetic** | `conftest.py:7` | `event_loop_policy` fixture is dead code |
| 7 | **Weak test** | `test_simulator_source.py:96` | `test_exception_resilience` doesn't actually inject an exception |

---

## Conformance to Design Specification

| Requirement | Status |
|---|---|
| `MarketDataSource` abstract interface | ✅ Correctly implemented |
| `PriceCache` thread-safe one-writer/many-readers | ✅ Lock on all mutations |
| `SimulatorDataSource` GBM with correct formula | ✅ Itô-corrected GBM verified |
| Correlated moves via Cholesky decomposition | ✅ Correctly implemented |
| Random events ~0.1% per tick | ✅ Implemented |
| `MassiveDataSource` polls via `asyncio.to_thread` | ✅ Correctly non-blocking |
| Factory selects implementation from env var | ✅ Whitespace-safe |
| SSE stream with `retry` directive | ✅ `retry: 1000` |
| `X-Accel-Buffering: no` for nginx compatibility | ✅ Present |
| Seed prices match design doc | ✅ All 10 tickers correct |
| Default seed prices for unknown tickers ($50-$300) | ✅ `random.uniform(50.0, 300.0)` |

---

## Conclusion

The market data backend is a high-quality implementation that meets the design specification. The code is readable, well-organized, and appropriately tested. The two bugs (global router mutation, `start()` normalization gap) are straightforward to fix. The weak tests and missing coverage items are low-risk given the demo context.

**Recommendation: Approve with minor fixes suggested above before integrating the broader application.**
