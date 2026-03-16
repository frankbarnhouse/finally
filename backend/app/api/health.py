"""Health check endpoint."""

from fastapi import APIRouter


def create_health_router() -> APIRouter:
    """Create the health check router."""
    router = APIRouter(prefix="/api", tags=["system"])

    @router.get("/health")
    async def health():
        return {"status": "ok"}

    return router
