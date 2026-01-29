# =============================================================================
# SDLC Agent - FastAPI Application
# =============================================================================
# Enterprise-grade FastAPI application with:
# - Structured logging
# - OpenTelemetry instrumentation
# - Rate limiting
# - CORS configuration
# - Health checks
# - Error handling
# =============================================================================

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any

import sentry_sdk
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse

from sdlc_agent.api.middleware import (
    CorrelationIdMiddleware,
    RateLimitMiddleware,
    RequestLoggingMiddleware,
)
from sdlc_agent.api.routes import api_router
from sdlc_agent.core.config import get_settings
from sdlc_agent.core.exceptions import SDLCAgentError
from sdlc_agent.core.logging import get_logger, setup_logging
from sdlc_agent.core.telemetry import (
    instrument_fastapi,
    instrument_httpx,
    instrument_redis,
    setup_telemetry,
)
from sdlc_agent.db import close_db, init_db

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan manager.

    Handles startup and shutdown events.
    """
    settings = get_settings()

    # Startup
    logger.info(
        "Starting SDLC Agent",
        environment=settings.app.app_env.value,
        debug=settings.app.debug,
    )

    # Setup logging
    setup_logging(settings)

    # Setup OpenTelemetry
    setup_telemetry(settings)
    instrument_httpx()
    instrument_redis()

    # Setup Sentry
    if settings.observability.sentry_dsn:
        sentry_sdk.init(
            dsn=settings.observability.sentry_dsn,
            environment=settings.observability.sentry_environment,
            traces_sample_rate=settings.observability.sentry_traces_sample_rate,
            enable_tracing=True,
        )
        logger.info("Sentry initialized")

    # Initialize database
    await init_db()

    logger.info("SDLC Agent started successfully")

    yield

    # Shutdown
    logger.info("Shutting down SDLC Agent")
    await close_db()
    logger.info("SDLC Agent shutdown complete")


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.

    Returns:
        FastAPI: Configured application instance
    """
    settings = get_settings()

    app = FastAPI(
        title="SDLC Agent API",
        description="Enterprise-grade Multi-Agent System for Software Development Lifecycle",
        version="0.1.0",
        docs_url="/docs" if settings.app.is_development else None,
        redoc_url="/redoc" if settings.app.is_development else None,
        openapi_url="/openapi.json" if settings.app.is_development else None,
        default_response_class=ORJSONResponse,
        lifespan=lifespan,
    )

    # Add middleware (order matters - first added = last executed)

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.api.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Correlation-ID"],
    )

    # Request logging
    app.add_middleware(RequestLoggingMiddleware)

    # Rate limiting
    app.add_middleware(
        RateLimitMiddleware,
        requests_per_window=settings.api.rate_limit_requests,
        window_seconds=settings.api.rate_limit_window_seconds,
    )

    # Correlation ID
    app.add_middleware(CorrelationIdMiddleware)

    # Exception handlers
    @app.exception_handler(SDLCAgentError)
    async def sdlc_agent_error_handler(
        request: Request, exc: SDLCAgentError
    ) -> ORJSONResponse:
        """Handle SDLC Agent errors."""
        logger.warning(
            "SDLC Agent error",
            error_code=exc.code,
            error_message=exc.message,
            details=exc.details,
        )

        status_code = _get_status_code_for_error(exc.code)
        return ORJSONResponse(
            status_code=status_code,
            content=exc.to_dict(),
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(
        request: Request, exc: Exception
    ) -> ORJSONResponse:
        """Handle unexpected errors."""
        logger.exception("Unhandled exception", exc_info=exc)

        if settings.app.is_development:
            content = {
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": str(exc),
                    "details": {"type": type(exc).__name__},
                }
            }
        else:
            content = {
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "An unexpected error occurred",
                    "details": {},
                }
            }

        return ORJSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=content,
        )

    # Include routers
    app.include_router(api_router, prefix=f"/api/{settings.api.version}")

    # OpenTelemetry instrumentation
    instrument_fastapi(app)

    return app


def _get_status_code_for_error(error_code: str) -> int:
    """Map error codes to HTTP status codes."""
    mapping = {
        "NOT_FOUND": status.HTTP_404_NOT_FOUND,
        "CONFLICT": status.HTTP_409_CONFLICT,
        "VALIDATION_ERROR": status.HTTP_422_UNPROCESSABLE_ENTITY,
        "AUTH_ERROR": status.HTTP_401_UNAUTHORIZED,
        "FORBIDDEN": status.HTTP_403_FORBIDDEN,
        "RATE_LIMIT": status.HTTP_429_TOO_MANY_REQUESTS,
        "LLM_RATE_LIMIT": status.HTTP_429_TOO_MANY_REQUESTS,
    }
    return mapping.get(error_code, status.HTTP_500_INTERNAL_SERVER_ERROR)


# Create application instance
app = create_app()
