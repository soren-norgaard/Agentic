# =============================================================================
# SDLC Agent - Health Check Routes
# =============================================================================

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Response, status

from sdlc_agent.core.config import get_settings
from sdlc_agent.core.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.get("/health", include_in_schema=False)
async def health_check() -> dict[str, Any]:
    """
    Basic health check endpoint.

    Returns:
        Health status
    """
    return {
        "status": "healthy",
        "timestamp": datetime.now(UTC).isoformat(),
    }


@router.get("/health/ready")
async def readiness_check(response: Response) -> dict[str, Any]:
    """
    Readiness check - verifies all dependencies are available.

    Returns:
        Detailed health status of all dependencies
    """
    settings = get_settings()
    checks: dict[str, dict[str, Any]] = {}
    all_healthy = True

    # Check database
    try:
        from sdlc_agent.db import get_session_context

        async with get_session_context() as session:
            await session.execute("SELECT 1")
        checks["database"] = {"status": "healthy"}
    except Exception as e:
        checks["database"] = {"status": "unhealthy", "error": str(e)}
        all_healthy = False
        logger.error("Database health check failed", error=str(e))

    # Check Redis
    try:
        import redis.asyncio as redis

        client = redis.from_url(str(settings.redis.url))
        await client.ping()
        await client.aclose()
        checks["redis"] = {"status": "healthy"}
    except Exception as e:
        checks["redis"] = {"status": "unhealthy", "error": str(e)}
        all_healthy = False
        logger.error("Redis health check failed", error=str(e))

    # Overall status
    if not all_healthy:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return {
        "status": "healthy" if all_healthy else "unhealthy",
        "timestamp": datetime.now(UTC).isoformat(),
        "checks": checks,
    }


@router.get("/health/live")
async def liveness_check() -> dict[str, Any]:
    """
    Liveness check - verifies the application is running.

    Returns:
        Basic liveness status
    """
    return {
        "status": "alive",
        "timestamp": datetime.now(UTC).isoformat(),
    }
