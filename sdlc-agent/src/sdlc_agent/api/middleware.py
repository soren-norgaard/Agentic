# =============================================================================
# SDLC Agent - API Middleware
# =============================================================================

from __future__ import annotations

import time
from collections import defaultdict
from typing import TYPE_CHECKING, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from sdlc_agent.core.logging import (
    get_correlation_id,
    get_logger,
    reset_correlation_id,
    set_correlation_id,
)
from sdlc_agent.core.telemetry import request_counter, request_duration

if TYPE_CHECKING:
    from starlette.types import ASGIApp

logger = get_logger(__name__)


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Middleware to handle correlation ID propagation."""

    HEADER_NAME = "X-Correlation-ID"

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Extract or generate correlation ID and add to response."""
        # Get from header or generate new
        correlation_id = request.headers.get(self.HEADER_NAME)
        if correlation_id:
            set_correlation_id(correlation_id)
        else:
            correlation_id = get_correlation_id()

        try:
            response = await call_next(request)
            response.headers[self.HEADER_NAME] = correlation_id
            return response
        finally:
            reset_correlation_id()


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for structured request/response logging."""

    SKIP_PATHS = {"/health", "/metrics", "/favicon.ico"}

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Log request and response details."""
        if request.url.path in self.SKIP_PATHS:
            return await call_next(request)

        start_time = time.perf_counter()

        # Log request
        logger.info(
            "Request started",
            method=request.method,
            path=request.url.path,
            query=str(request.query_params),
            client_ip=request.client.host if request.client else None,
        )

        try:
            response = await call_next(request)
            duration = time.perf_counter() - start_time

            # Log response
            logger.info(
                "Request completed",
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration_ms=round(duration * 1000, 2),
            )

            # Record metrics
            labels = {
                "method": request.method,
                "path": request.url.path,
                "status_code": str(response.status_code),
            }
            request_counter.add(1, labels)
            request_duration.record(duration, labels)

            return response

        except Exception as exc:
            duration = time.perf_counter() - start_time
            logger.exception(
                "Request failed",
                method=request.method,
                path=request.url.path,
                duration_ms=round(duration * 1000, 2),
            )
            raise


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple in-memory rate limiting middleware."""

    def __init__(
        self,
        app: ASGIApp,
        requests_per_window: int = 100,
        window_seconds: int = 60,
    ) -> None:
        super().__init__(app)
        self.requests_per_window = requests_per_window
        self.window_seconds = window_seconds
        self._request_counts: dict[str, list[float]] = defaultdict(list)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Check rate limits before processing request."""
        # Skip rate limiting for health checks
        if request.url.path in {"/health", "/metrics"}:
            return await call_next(request)

        # Get client identifier (IP or API key)
        client_id = self._get_client_id(request)
        current_time = time.time()
        window_start = current_time - self.window_seconds

        # Clean old entries and count requests in window
        self._request_counts[client_id] = [
            ts for ts in self._request_counts[client_id] if ts > window_start
        ]

        if len(self._request_counts[client_id]) >= self.requests_per_window:
            logger.warning(
                "Rate limit exceeded",
                client_id=client_id,
                requests=len(self._request_counts[client_id]),
            )
            return Response(
                content='{"error": {"code": "RATE_LIMIT", "message": "Rate limit exceeded"}}',
                status_code=429,
                media_type="application/json",
                headers={
                    "Retry-After": str(self.window_seconds),
                    "X-RateLimit-Limit": str(self.requests_per_window),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(window_start + self.window_seconds)),
                },
            )

        # Record this request
        self._request_counts[client_id].append(current_time)
        remaining = self.requests_per_window - len(self._request_counts[client_id])

        response = await call_next(request)

        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(self.requests_per_window)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int(window_start + self.window_seconds))

        return response

    def _get_client_id(self, request: Request) -> str:
        """Get client identifier from request."""
        # Prefer API key over IP
        api_key = request.headers.get("X-API-Key")
        if api_key:
            return f"key:{api_key[:8]}"  # Use prefix for privacy

        # Fall back to IP
        if request.client:
            return f"ip:{request.client.host}"

        return "unknown"
