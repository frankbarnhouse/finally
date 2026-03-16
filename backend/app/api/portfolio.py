"""Portfolio REST endpoints: view portfolio and execute trades."""

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.market import PriceCache
from app.services.portfolio import execute_trade, get_portfolio


class TradeRequest(BaseModel):
    """Market order request."""

    ticker: str
    quantity: float = Field(gt=0)
    side: str  # "buy" or "sell"


def create_portfolio_router(price_cache: PriceCache) -> APIRouter:
    """Create the portfolio router with injected price cache."""
    router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])

    @router.get("")
    async def get_portfolio_endpoint():
        return await get_portfolio(price_cache)

    @router.post("/trade")
    async def trade_endpoint(req: TradeRequest):
        result, error = await execute_trade(
            price_cache, req.ticker.upper(), req.side, req.quantity
        )
        if error:
            return JSONResponse(status_code=400, content={"error": error})
        return result

    return router
