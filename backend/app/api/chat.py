"""Chat API endpoint."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from app.db import get_db
from app.llm.chat import handle_chat_message
from app.market import PriceCache
from app.trade import execute_trade

router = APIRouter(prefix="/api", tags=["chat"])

_price_cache: PriceCache | None = None


def init_chat_router(price_cache: PriceCache) -> None:
    """Inject the price cache dependency."""
    global _price_cache
    _price_cache = price_cache


class ChatRequest(BaseModel):
    message: str


@router.post("/chat")
async def chat(body: ChatRequest) -> dict:
    """Send a message to the AI assistant."""
    db = await get_db()

    async def trade_fn(db, ticker, side, quantity, price_cache):
        return await execute_trade(db, ticker, side, quantity, price_cache)

    return await handle_chat_message(
        user_message=body.message,
        db=db,
        price_cache=_price_cache,
        execute_trade_fn=trade_fn,
    )
