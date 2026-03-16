"""Chat REST endpoint: LLM-powered trading assistant."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from app.services.chat import handle_chat_message


class ChatRequest(BaseModel):
    """Incoming chat message from the user."""

    message: str


def create_chat_router(price_cache, data_source) -> APIRouter:
    """Create the chat router with injected dependencies."""
    router = APIRouter(prefix="/api", tags=["chat"])

    @router.post("/chat")
    async def chat_endpoint(req: ChatRequest):
        return await handle_chat_message(req.message, price_cache, data_source)

    return router
