# =============================================================================
# SDLC Agent - Custom Exceptions
# =============================================================================
# Hierarchical exception system for proper error handling and propagation.
# =============================================================================

from __future__ import annotations

from typing import Any


class SDLCAgentError(Exception):
    """Base exception for all SDLC Agent errors."""

    def __init__(
        self,
        message: str,
        *,
        code: str = "SDLC_ERROR",
        details: dict[str, Any] | None = None,
    ) -> None:
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(message)

    def to_dict(self) -> dict[str, Any]:
        """Convert exception to dictionary for API responses."""
        return {
            "error": {
                "code": self.code,
                "message": self.message,
                "details": self.details,
            }
        }


# =============================================================================
# Configuration Errors
# =============================================================================


class ConfigurationError(SDLCAgentError):
    """Configuration-related errors."""

    def __init__(self, message: str, **kwargs: Any) -> None:
        super().__init__(message, code="CONFIG_ERROR", **kwargs)


class MissingConfigError(ConfigurationError):
    """Missing required configuration."""

    def __init__(self, config_key: str, **kwargs: Any) -> None:
        super().__init__(
            f"Missing required configuration: {config_key}",
            details={"config_key": config_key},
            **kwargs,
        )


# =============================================================================
# Authentication & Authorization Errors
# =============================================================================


class AuthError(SDLCAgentError):
    """Authentication-related errors."""

    def __init__(self, message: str = "Authentication failed", **kwargs: Any) -> None:
        super().__init__(message, code="AUTH_ERROR", **kwargs)


class InvalidCredentialsError(AuthError):
    """Invalid credentials provided."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(message="Invalid credentials", **kwargs)


class TokenExpiredError(AuthError):
    """Authentication token has expired."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(message="Token has expired", **kwargs)


class InsufficientPermissionsError(AuthError):
    """User lacks required permissions."""

    def __init__(self, required_permission: str, **kwargs: Any) -> None:
        super().__init__(
            message=f"Insufficient permissions: {required_permission} required",
            code="FORBIDDEN",
            details={"required_permission": required_permission},
            **kwargs,
        )


# =============================================================================
# Database Errors
# =============================================================================


class DatabaseError(SDLCAgentError):
    """Database-related errors."""

    def __init__(self, message: str, code: str = "DATABASE_ERROR", **kwargs: Any) -> None:
        super().__init__(message, code=code, **kwargs)


class EntityNotFoundError(DatabaseError):
    """Requested entity not found."""

    def __init__(
        self, entity_type: str, entity_id: str | int, **kwargs: Any
    ) -> None:
        # Remove code from kwargs if present to avoid duplicate
        kwargs.pop("code", None)
        super().__init__(
            message=f"{entity_type} with ID {entity_id} not found",
            code="NOT_FOUND",
            details={"entity_type": entity_type, "entity_id": str(entity_id)},
            **kwargs,
        )


class DuplicateEntityError(DatabaseError):
    """Entity already exists."""

    def __init__(self, entity_type: str, identifier: str, **kwargs: Any) -> None:
        # Remove code from kwargs if present to avoid duplicate
        kwargs.pop("code", None)
        super().__init__(
            message=f"{entity_type} with identifier {identifier} already exists",
            code="CONFLICT",
            details={"entity_type": entity_type, "identifier": identifier},
            **kwargs,
        )


# =============================================================================
# Agent Errors
# =============================================================================


class AgentError(SDLCAgentError):
    """Agent execution errors."""

    def __init__(self, message: str, **kwargs: Any) -> None:
        super().__init__(message, code="AGENT_ERROR", **kwargs)


class AgentTimeoutError(AgentError):
    """Agent execution timed out."""

    def __init__(self, agent_name: str, timeout_seconds: int, **kwargs: Any) -> None:
        super().__init__(
            message=f"Agent {agent_name} timed out after {timeout_seconds} seconds",
            code="AGENT_TIMEOUT",
            details={"agent_name": agent_name, "timeout_seconds": timeout_seconds},
            **kwargs,
        )


class AgentMaxIterationsError(AgentError):
    """Agent exceeded maximum iterations."""

    def __init__(self, agent_name: str, max_iterations: int, **kwargs: Any) -> None:
        super().__init__(
            message=f"Agent {agent_name} exceeded {max_iterations} iterations",
            code="AGENT_MAX_ITERATIONS",
            details={"agent_name": agent_name, "max_iterations": max_iterations},
            **kwargs,
        )


class AgentToolError(AgentError):
    """Agent tool execution error."""

    def __init__(self, tool_name: str, error_message: str, **kwargs: Any) -> None:
        super().__init__(
            message=f"Tool {tool_name} failed: {error_message}",
            code="AGENT_TOOL_ERROR",
            details={"tool_name": tool_name, "error_message": error_message},
            **kwargs,
        )


# =============================================================================
# LLM Errors
# =============================================================================


class LLMError(SDLCAgentError):
    """LLM provider errors."""

    def __init__(self, message: str, **kwargs: Any) -> None:
        super().__init__(message, code="LLM_ERROR", **kwargs)


class LLMRateLimitError(LLMError):
    """LLM rate limit exceeded."""

    def __init__(self, provider: str, retry_after: int | None = None, **kwargs: Any) -> None:
        super().__init__(
            message=f"Rate limit exceeded for {provider}",
            code="LLM_RATE_LIMIT",
            details={"provider": provider, "retry_after": retry_after},
            **kwargs,
        )


class LLMContextLengthError(LLMError):
    """LLM context length exceeded."""

    def __init__(self, max_tokens: int, actual_tokens: int, **kwargs: Any) -> None:
        super().__init__(
            message=f"Context length exceeded: {actual_tokens} > {max_tokens}",
            code="LLM_CONTEXT_LENGTH",
            details={"max_tokens": max_tokens, "actual_tokens": actual_tokens},
            **kwargs,
        )


# =============================================================================
# Validation Errors
# =============================================================================


class ValidationError(SDLCAgentError):
    """Input validation errors."""

    def __init__(
        self,
        message: str,
        field: str | None = None,
        **kwargs: Any,
    ) -> None:
        details = kwargs.pop("details", {})
        if field:
            details["field"] = field
        super().__init__(
            message,
            code="VALIDATION_ERROR",
            details=details,
            **kwargs,
        )


# =============================================================================
# External Service Errors
# =============================================================================


class ExternalServiceError(SDLCAgentError):
    """External service integration errors."""

    def __init__(
        self,
        service_name: str,
        message: str,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            message=f"{service_name}: {message}",
            code="EXTERNAL_SERVICE_ERROR",
            details={"service_name": service_name},
            **kwargs,
        )


class GitHubError(ExternalServiceError):
    """GitHub API errors."""

    def __init__(self, message: str, **kwargs: Any) -> None:
        super().__init__("GitHub", message, **kwargs)


class JiraError(ExternalServiceError):
    """Jira API errors."""

    def __init__(self, message: str, **kwargs: Any) -> None:
        super().__init__("Jira", message, **kwargs)
