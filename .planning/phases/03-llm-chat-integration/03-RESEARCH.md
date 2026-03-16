# Phase 3: LLM Chat Integration - Research

**Researched:** 2026-03-16
**Domain:** LLM integration (LiteLLM + Gemini), structured outputs, auto-execution
**Confidence:** HIGH

## Summary

Phase 3 adds an AI chat assistant that understands the user's portfolio and can execute trades and manage the watchlist through natural language. The core technology is LiteLLM calling Google's `gemini/gemini-3.1-flash-lite-preview` model with structured JSON output. The existing service layer from Phase 2 (`execute_trade`, `add_ticker`, `remove_ticker`) is designed for direct reuse -- this was an explicit Phase 2 design decision.

The main integration work involves: (1) a chat service that assembles context, calls the LLM, parses structured output, and auto-executes actions, (2) a chat API router following the established factory pattern, and (3) a mock mode for deterministic testing without API calls. The `chat_messages` table already exists in the schema.

**Primary recommendation:** Use LiteLLM's `acompletion` with a Pydantic `response_format` model for structured output. Bridge `GOOGLE_API_KEY` to `GEMINI_API_KEY` at startup. Implement mock mode as a service-level bypass (not LiteLLM's built-in `mock_response`) to return deterministic, schema-valid JSON.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| CHAT-01 | User can send messages and receive AI responses with full portfolio context | LiteLLM acompletion with system prompt containing portfolio state; chat service assembles context from get_portfolio + get_watchlist + last 10 messages |
| CHAT-02 | AI can auto-execute trades via structured JSON output | Pydantic response model with `trades` field; iterate and call execute_trade for each |
| CHAT-03 | AI can add/remove watchlist tickers via structured JSON output | Pydantic response model with `watchlist_changes` field; iterate and call add_ticker/remove_ticker |
| CHAT-04 | Last 10 conversation messages included in LLM context | Query chat_messages table ORDER BY created_at DESC LIMIT 10, reverse for chronological order |
| CHAT-05 | LLM mock mode returns deterministic responses when LLM_MOCK=true | Service-level bypass: check env var, return hardcoded schema-valid response without calling LiteLLM |
| CHAT-06 | Failed trade/watchlist actions appended to response message text | Collect errors from execute_trade/add_ticker results, append to message string |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| litellm | 1.82.2 | LLM API abstraction | Already installed; provides `acompletion` with Gemini support and structured output |
| pydantic | 2.12.5 | Structured output schema | Already installed; LiteLLM accepts Pydantic models as `response_format` |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| aiosqlite | 0.22.0+ | Async SQLite (chat_messages table) | Already installed; same DB access pattern as Phase 2 |
| python-dotenv | (bundled with litellm) | Environment variable loading | Already a litellm dependency; for reading GOOGLE_API_KEY |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| LiteLLM structured output | instructor library | Adds retry logic but extra dependency; LiteLLM native is sufficient |
| Service-level mock | LiteLLM mock_response param | mock_response returns plain text, not structured JSON matching our schema |

**Installation:**
```bash
# No new packages needed -- litellm and pydantic already installed
cd backend && uv sync --extra dev
```

## Architecture Patterns

### Recommended Project Structure
```
backend/app/
├── services/
│   ├── portfolio.py      # Existing - reuse execute_trade, get_portfolio
│   ├── watchlist.py       # Existing - reuse add_ticker, remove_ticker
│   └── chat.py            # NEW - chat service (LLM call, context assembly, action execution)
├── api/
│   └── chat.py            # NEW - POST /api/chat router (factory pattern)
└── main.py                # Wire chat router into app
```

### Pattern 1: Chat Service Layer
**What:** Single async function `handle_chat_message(message, price_cache, data_source)` that orchestrates the full flow: load context, call LLM, parse response, execute actions, store messages, return result.
**When to use:** Every chat request.
**Example:**
```python
# backend/app/services/chat.py
import json
import os
import uuid
from datetime import datetime, timezone
from pydantic import BaseModel, Field
from litellm import acompletion
from app.db import get_db
from app.services.portfolio import execute_trade, get_portfolio
from app.services.watchlist import get_watchlist, add_ticker, remove_ticker


class TradeAction(BaseModel):
    ticker: str
    side: str
    quantity: float

class WatchlistChange(BaseModel):
    ticker: str
    action: str  # "add" or "remove"

class ChatResponse(BaseModel):
    message: str
    trades: list[TradeAction] = Field(default_factory=list)
    watchlist_changes: list[WatchlistChange] = Field(default_factory=list)


SYSTEM_PROMPT = """You are FinAlly, an AI trading assistant..."""


async def handle_chat_message(
    user_message: str,
    price_cache,
    data_source,
) -> dict:
    # 1. Load portfolio context
    portfolio = await get_portfolio(price_cache)
    watchlist = await get_watchlist(price_cache)

    # 2. Load last 10 messages
    db = await get_db()
    cursor = await db.execute(
        "SELECT role, content FROM chat_messages WHERE user_id = ? "
        "ORDER BY created_at DESC LIMIT 10",
        ("default",),
    )
    rows = await cursor.fetchall()
    history = [{"role": r[0], "content": r[1]} for r in reversed(rows)]

    # 3. Build messages
    context_block = format_portfolio_context(portfolio, watchlist)
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT + "\n\n" + context_block},
        *history,
        {"role": "user", "content": user_message},
    ]

    # 4. Call LLM (or mock)
    if os.environ.get("LLM_MOCK", "").lower() == "true":
        parsed = mock_response(user_message)
    else:
        os.environ.setdefault("GEMINI_API_KEY", os.environ.get("GOOGLE_API_KEY", ""))
        response = await acompletion(
            model="gemini/gemini-3.1-flash-lite-preview",
            messages=messages,
            response_format=ChatResponse,
        )
        parsed = ChatResponse.model_validate_json(
            response.choices[0].message.content
        )

    # 5. Auto-execute actions, collect errors
    errors = []
    executed_trades = []
    for trade in parsed.trades:
        result, error = await execute_trade(
            price_cache, trade.ticker.upper(), trade.side, trade.quantity
        )
        if error:
            errors.append(f"Trade failed ({trade.side} {trade.quantity} {trade.ticker}): {error}")
        else:
            executed_trades.append(result["trade"])

    executed_watchlist = []
    for change in parsed.watchlist_changes:
        try:
            if change.action == "add":
                await add_ticker(change.ticker, price_cache, data_source)
                executed_watchlist.append({"ticker": change.ticker.upper(), "action": "add"})
            elif change.action == "remove":
                await remove_ticker(change.ticker, data_source)
                executed_watchlist.append({"ticker": change.ticker.upper(), "action": "remove"})
        except Exception as e:
            errors.append(f"Watchlist {change.action} {change.ticker} failed: {e}")

    # 6. Append errors to message
    final_message = parsed.message
    if errors:
        final_message += "\n\n" + "\n".join(errors)

    # 7. Store messages in DB
    now = datetime.now(timezone.utc).isoformat()
    actions_json = json.dumps({
        "trades": [t for t in executed_trades],
        "watchlist_changes": executed_watchlist,
    }) if (executed_trades or executed_watchlist) else None

    await db.execute(
        "INSERT INTO chat_messages (id, user_id, role, content, actions, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (str(uuid.uuid4()), "default", "user", user_message, None, now),
    )
    await db.execute(
        "INSERT INTO chat_messages (id, user_id, role, content, actions, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (str(uuid.uuid4()), "default", "assistant", final_message, actions_json, now),
    )
    await db.commit()

    return {
        "message": final_message,
        "actions": {
            "trades": executed_trades,
            "watchlist_changes": executed_watchlist,
        },
    }
```

### Pattern 2: Router Factory (Established)
**What:** `create_chat_router(price_cache, data_source)` following the same pattern as portfolio and watchlist routers.
**Example:**
```python
# backend/app/api/chat.py
from fastapi import APIRouter
from pydantic import BaseModel
from app.services.chat import handle_chat_message

class ChatRequest(BaseModel):
    message: str

def create_chat_router(price_cache, data_source) -> APIRouter:
    router = APIRouter(prefix="/api", tags=["chat"])

    @router.post("/chat")
    async def chat_endpoint(req: ChatRequest):
        return await handle_chat_message(req.message, price_cache, data_source)

    return router
```

### Pattern 3: Mock Mode (Service-Level Bypass)
**What:** When `LLM_MOCK=true`, return a deterministic `ChatResponse` without calling LiteLLM.
**Why not use LiteLLM's built-in mock_response:** LiteLLM's `mock_response` returns plain text, not structured JSON matching our Pydantic schema. A service-level bypass gives us full control over the mock shape.
**Example:**
```python
def mock_response(user_message: str) -> ChatResponse:
    """Return deterministic mock response for testing."""
    msg = user_message.lower()
    if "buy" in msg:
        # Parse simple "buy X shares of Y" patterns for test determinism
        return ChatResponse(
            message="Mock: Executing buy order as requested.",
            trades=[TradeAction(ticker="AAPL", side="buy", quantity=10)],
            watchlist_changes=[],
        )
    if "add" in msg and "watchlist" in msg:
        return ChatResponse(
            message="Mock: Adding ticker to watchlist.",
            trades=[],
            watchlist_changes=[WatchlistChange(ticker="PYPL", action="add")],
        )
    return ChatResponse(
        message="Mock: I can help you with your portfolio. You have positions and cash available for trading.",
        trades=[],
        watchlist_changes=[],
    )
```

### Anti-Patterns to Avoid
- **Calling LiteLLM synchronously:** Always use `acompletion`, never `completion` -- this is an async FastAPI app.
- **Storing raw LLM response in DB:** Store the parsed `message` string, not the full LLM API response object.
- **Confirmation dialogs for AI trades:** PLAN.md explicitly says no confirmation -- auto-execute immediately.
- **Streaming LLM responses:** Out of scope per REQUIREMENTS.md -- structured output requires complete JSON.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| LLM API calls | Custom HTTP client for Gemini | LiteLLM `acompletion` | Handles auth, retries, response parsing, model routing |
| Structured output parsing | Manual JSON parsing + validation | Pydantic model as `response_format` | LiteLLM + Pydantic handles schema enforcement and validation |
| Trade execution | New trade logic in chat service | `execute_trade` from portfolio service | Already tested with 11 service-level tests, handles all edge cases |
| Watchlist management | New watchlist logic in chat service | `add_ticker`/`remove_ticker` from watchlist service | Already tested, handles position-aware removal |

**Key insight:** Phase 2 was explicitly designed so that service functions are callable directly from the chat service. The entire purpose of service-layer separation was to enable this reuse.

## Common Pitfalls

### Pitfall 1: Wrong Environment Variable Name
**What goes wrong:** LiteLLM expects `GEMINI_API_KEY` but the project uses `GOOGLE_API_KEY` in `.env`.
**Why it happens:** Different naming conventions between Google's SDK and LiteLLM.
**How to avoid:** At service initialization, bridge: `os.environ.setdefault("GEMINI_API_KEY", os.environ.get("GOOGLE_API_KEY", ""))`. Or pass `api_key=` directly to `acompletion`.
**Warning signs:** "AuthenticationError" or "API key not found" when calling LiteLLM.

### Pitfall 2: LLM Returns Invalid JSON Despite Schema
**What goes wrong:** Even with structured output, the model may occasionally return malformed JSON or JSON that doesn't match the schema.
**Why it happens:** Preview models have less reliable structured output adherence.
**How to avoid:** Wrap `ChatResponse.model_validate_json()` in try/except. On failure, return a user-friendly error message. STATE.md notes: "gemini-3.1-flash-lite-preview is a preview model; structured output adherence needs runtime verification. Fallback: gemini-2.0-flash-lite."
**Warning signs:** `ValidationError` from Pydantic when parsing LLM output.

### Pitfall 3: Message History Context Window
**What goes wrong:** Including too many messages or too much portfolio context exceeds the model's context window or produces poor responses.
**Why it happens:** System prompt + portfolio context + 10 messages can get long.
**How to avoid:** Limit to last 10 messages (per spec). Keep portfolio context concise -- just the essential numbers, not full trade history.

### Pitfall 4: Mock Mode Returns Non-Deterministic Results
**What goes wrong:** E2E tests become flaky because mock responses vary.
**Why it happens:** Mock logic tries to be too smart about parsing user intent.
**How to avoid:** Keep mock responses simple and keyword-based. Document exact mock behaviors for test writers.

### Pitfall 5: Race Condition on Concurrent Chat Requests
**What goes wrong:** Two simultaneous chat messages could cause duplicate trade executions.
**Why it happens:** `execute_trade` uses BEGIN IMMEDIATE (serialized), but two chat requests could both read the same portfolio state.
**How to avoid:** Single-user app mitigates this. The BEGIN IMMEDIATE in execute_trade provides transaction-level safety for individual trades.

## Code Examples

### LiteLLM acompletion with Structured Output (Pydantic)
```python
# Source: https://docs.litellm.ai/docs/completion/json_mode
from litellm import acompletion
from pydantic import BaseModel

class ChatResponse(BaseModel):
    message: str
    trades: list[dict] = []
    watchlist_changes: list[dict] = []

response = await acompletion(
    model="gemini/gemini-3.1-flash-lite-preview",
    messages=[
        {"role": "system", "content": "You are FinAlly..."},
        {"role": "user", "content": "Buy 10 shares of AAPL"},
    ],
    response_format=ChatResponse,
)
parsed = ChatResponse.model_validate_json(response.choices[0].message.content)
```

### Bridging GOOGLE_API_KEY to GEMINI_API_KEY
```python
import os

# At module level or service init
api_key = os.environ.get("GOOGLE_API_KEY", "")

# Pass directly to acompletion
response = await acompletion(
    model="gemini/gemini-3.1-flash-lite-preview",
    messages=messages,
    response_format=ChatResponse,
    api_key=api_key,
)
```

### System Prompt with Portfolio Context
```python
SYSTEM_PROMPT = """You are FinAlly, an AI trading assistant for a simulated portfolio.

You can analyze the user's portfolio, suggest trades, and execute trades when asked.
You can also manage the watchlist by adding or removing tickers.

Always respond with valid JSON matching the required schema:
- "message": Your conversational response
- "trades": Array of trades to execute [{ticker, side, quantity}]
- "watchlist_changes": Array of watchlist changes [{ticker, action}]
  where action is "add" or "remove"

Be concise and data-driven. When the user asks you to trade, include the trade in your response.
When suggesting trades, explain your reasoning briefly."""


def format_portfolio_context(portfolio: dict, watchlist: list[dict]) -> str:
    positions_text = "\n".join(
        f"  {p['ticker']}: {p['quantity']} shares @ ${p['avg_cost']:.2f} "
        f"(current: ${p['current_price']:.2f}, P&L: ${p['unrealized_pnl']:.2f})"
        for p in portfolio["positions"]
    ) or "  No positions"

    watchlist_text = ", ".join(
        f"{w['ticker']}=${w['price']:.2f}" if w['price'] else w['ticker']
        for w in watchlist
    ) or "Empty"

    return (
        f"PORTFOLIO STATE:\n"
        f"Cash: ${portfolio['cash_balance']:.2f}\n"
        f"Total Value: ${portfolio['total_value']:.2f}\n"
        f"Positions:\n{positions_text}\n"
        f"Watchlist: {watchlist_text}"
    )
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| json_object response_format | Pydantic model as response_format | LiteLLM ~1.50+ | Direct schema enforcement, no manual JSON parsing |
| GOOGLE_API_KEY env var | GEMINI_API_KEY for LiteLLM | LiteLLM Gemini provider | Must bridge env var or pass api_key directly |
| Gemini 2.0 flash lite | Gemini 3.1 flash lite preview | 2025-2026 | Newer model, structured output support, preview status |

## Open Questions

1. **Gemini 3.1 flash lite preview reliability**
   - What we know: It is a preview model listed in LiteLLM's model registry. STATE.md flags it as a concern.
   - What's unclear: How reliably it adheres to structured output schemas in practice.
   - Recommendation: Implement with gemini-3.1-flash-lite-preview as primary. Add try/except around parsing. If validation fails, the error message should tell the user to try again. Consider a fallback model constant (`gemini/gemini-2.0-flash-lite`) that can be swapped in easily.

2. **Error handling granularity for partial action failures**
   - What we know: PLAN.md says "append error to message string." Multiple trades could partially succeed.
   - What's unclear: Should we report individual trade success alongside failures?
   - Recommendation: Execute all actions, collect all errors, append all errors to message. Return successfully executed actions in the response `actions` field so the frontend can show confirmations.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.3+ with pytest-asyncio |
| Config file | backend/pyproject.toml |
| Quick run command | `cd backend && uv run pytest tests/llm/ -x -v` |
| Full suite command | `cd backend && uv run pytest -v` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CHAT-01 | Chat returns AI response with portfolio context | unit | `uv run pytest tests/services/test_chat.py::test_chat_returns_response -x` | Wave 0 |
| CHAT-02 | AI trade actions auto-execute | unit | `uv run pytest tests/services/test_chat.py::test_trade_auto_execution -x` | Wave 0 |
| CHAT-03 | AI watchlist changes auto-execute | unit | `uv run pytest tests/services/test_chat.py::test_watchlist_auto_execution -x` | Wave 0 |
| CHAT-04 | Last 10 messages loaded into context | unit | `uv run pytest tests/services/test_chat.py::test_message_history_limit -x` | Wave 0 |
| CHAT-05 | Mock mode returns deterministic response | unit | `uv run pytest tests/services/test_chat.py::test_mock_mode -x` | Wave 0 |
| CHAT-06 | Failed actions appended to message | unit | `uv run pytest tests/services/test_chat.py::test_failed_action_appended -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `cd backend && uv run pytest tests/services/test_chat.py tests/api/test_chat.py -x -v`
- **Per wave merge:** `cd backend && uv run pytest -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/services/test_chat.py` -- covers CHAT-01 through CHAT-06 (service-level tests with mocked LLM)
- [ ] `tests/api/test_chat.py` -- covers HTTP endpoint (POST /api/chat)
- [ ] `tests/llm/__init__.py` -- package init (directory exists but empty except __pycache__)

## Sources

### Primary (HIGH confidence)
- LiteLLM docs: structured output / JSON mode -- https://docs.litellm.ai/docs/completion/json_mode
- LiteLLM docs: Gemini provider -- https://docs.litellm.ai/docs/providers/gemini
- LiteLLM docs: mock requests -- https://docs.litellm.ai/docs/completion/mock_requests
- LiteLLM Gemini 3 support -- https://docs.litellm.ai/blog/gemini_3
- Verified: litellm 1.82.2 installed, `acompletion` available, model `gemini/gemini-3.1-flash-lite-preview` in model registry

### Secondary (MEDIUM confidence)
- LiteLLM env var naming: GEMINI_API_KEY (verified via official docs, multiple sources)
- Pydantic model as response_format (verified via official docs code examples)

### Tertiary (LOW confidence)
- gemini-3.1-flash-lite-preview structured output reliability (preview model, no production track record)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - litellm 1.82.2 already installed, Pydantic 2.12.5 already installed, API verified
- Architecture: HIGH - follows established service-layer and router-factory patterns from Phase 2
- Pitfalls: HIGH - env var naming verified against official docs, preview model concern documented in STATE.md

**Research date:** 2026-03-16
**Valid until:** 2026-04-16 (litellm updates frequently but core acompletion API is stable)
