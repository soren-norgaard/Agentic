# =============================================================================
# SDLC Agent - Settings Routes
# =============================================================================

from __future__ import annotations

import json
from typing import Any

import redis.asyncio as redis
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from sdlc_agent.core.config import LLMProvider, get_settings
from sdlc_agent.core.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)

# Redis keys for settings
LLM_SETTINGS_KEY = "sdlc:settings:llm"
WORKFLOW_SETTINGS_KEY = "sdlc:settings:workflow"

# Default workflow settings
DEFAULT_MAX_ITERATIONS = 100


async def _get_redis() -> redis.Redis:
    """Get Redis client."""
    settings = get_settings()
    return redis.from_url(str(settings.redis.url))


async def get_llm_settings_from_redis() -> dict[str, Any] | None:
    """Get LLM settings from Redis."""
    try:
        client = await _get_redis()
        data = await client.get(LLM_SETTINGS_KEY)
        await client.aclose()
        if data:
            return json.loads(data)
    except Exception as e:
        logger.warning("Failed to get LLM settings from Redis", error=str(e))
    return None


async def set_llm_settings_in_redis(settings_data: dict[str, Any]) -> None:
    """Store LLM settings in Redis."""
    try:
        client = await _get_redis()
        await client.set(LLM_SETTINGS_KEY, json.dumps(settings_data))
        await client.aclose()
        logger.info("LLM settings saved to Redis", settings=settings_data)
    except Exception as e:
        logger.error("Failed to save LLM settings to Redis", error=str(e))


async def get_workflow_settings_from_redis() -> dict[str, Any] | None:
    """Get workflow settings from Redis."""
    try:
        client = await _get_redis()
        data = await client.get(WORKFLOW_SETTINGS_KEY)
        await client.aclose()
        if data:
            return json.loads(data)
    except Exception as e:
        logger.warning("Failed to get workflow settings from Redis", error=str(e))
    return None


async def set_workflow_settings_in_redis(settings_data: dict[str, Any]) -> None:
    """Store workflow settings in Redis."""
    try:
        client = await _get_redis()
        await client.set(WORKFLOW_SETTINGS_KEY, json.dumps(settings_data))
        await client.aclose()
        logger.info("Workflow settings saved to Redis", settings=settings_data)
    except Exception as e:
        logger.error("Failed to save workflow settings to Redis", error=str(e))


# =============================================================================
# Schemas
# =============================================================================


class LLMModelOption(BaseModel):
    """Available LLM model option."""
    id: str
    name: str
    provider: str
    description: str | None = None


class LLMConfigResponse(BaseModel):
    """Current LLM configuration."""
    current_provider: str
    current_model: str
    available_models: list[LLMModelOption]
    temperature: float
    max_tokens: int


class LLMConfigUpdate(BaseModel):
    """Update LLM configuration."""
    model: str = Field(..., description="The model ID to use")
    temperature: float | None = Field(None, ge=0.0, le=2.0, description="Temperature (0-2)")
    max_tokens: int | None = Field(None, ge=1, le=128000, description="Max tokens")


# Available models configuration
AVAILABLE_MODELS: list[LLMModelOption] = [
    # OpenAI models
    LLMModelOption(
        id="gpt-4o-2024-08-06",
        name="GPT-4o",
        provider="openai",
        description="Fast, capable model for most tasks",
    ),
    LLMModelOption(
        id="gpt-4-turbo",
        name="GPT-4 Turbo",
        provider="openai",
        description="Latest GPT-4 with improved capabilities",
    ),
    LLMModelOption(
        id="gpt-5-2025-08-07",
        name="GPT-5",
        provider="openai",
        description="Most advanced OpenAI model",
    ),
    # Anthropic models
    LLMModelOption(
        id="anthropic.claude-sonnet-4-5-20250929-v1:0",
        name="Claude Sonnet 4.5",
        provider="anthropic",
        description="Balanced performance and cost",
    ),
    LLMModelOption(
        id="anthropic.claude-opus-4-5-20251101-v1:0",
        name="Claude Opus 4.5",
        provider="anthropic",
        description="Most capable Anthropic model",
    ),
    LLMModelOption(
        id="anthropic.claude-3-5-sonnet-20241022-v2:0",
        name="Claude 3.5 Sonnet",
        provider="anthropic",
        description="Fast and efficient for code tasks",
    ),
]


# In-memory fallback (Redis is primary)
_config_override: dict[str, Any] = {}


# =============================================================================
# Routes
# =============================================================================


@router.get("/llm", response_model=LLMConfigResponse)
async def get_llm_config() -> dict[str, Any]:
    """Get current LLM configuration and available models."""
    settings = get_settings()
    
    # Try Redis first, fall back to in-memory
    redis_settings = await get_llm_settings_from_redis()
    config = redis_settings or _config_override
    
    current_model = config.get("model", settings.llm.default_llm_model)
    current_temp = config.get("temperature", settings.llm.default_llm_temperature)
    current_tokens = config.get("max_tokens", settings.llm.default_llm_max_tokens)
    
    # Determine provider from model
    provider = "openai"
    if current_model.startswith("anthropic.") or current_model.startswith("claude-"):
        provider = "anthropic"
    
    return {
        "current_provider": provider,
        "current_model": current_model,
        "available_models": [m.model_dump() for m in AVAILABLE_MODELS],
        "temperature": current_temp,
        "max_tokens": current_tokens,
    }


@router.put("/llm", response_model=LLMConfigResponse)
async def update_llm_config(config: LLMConfigUpdate) -> dict[str, Any]:
    """Update LLM configuration."""
    global _config_override
    
    # Validate model exists
    valid_models = {m.id for m in AVAILABLE_MODELS}
    if config.model not in valid_models:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid model: {config.model}. Available models: {list(valid_models)}",
        )
    
    # Build settings dict
    new_settings = {"model": config.model}
    if config.temperature is not None:
        new_settings["temperature"] = config.temperature
    if config.max_tokens is not None:
        new_settings["max_tokens"] = config.max_tokens
    
    # Store in Redis (shared with workers)
    await set_llm_settings_in_redis(new_settings)
    
    # Also update in-memory fallback
    _config_override.update(new_settings)
    
    logger.info(
        "LLM config updated and saved to Redis",
        model=config.model,
        temperature=config.temperature,
        max_tokens=config.max_tokens,
    )
    
    return await get_llm_config()


@router.post("/llm/test")
async def test_llm_connection() -> dict[str, Any]:
    """Test the current LLM configuration."""
    from sdlc_agent.services import LLMClient
    
    settings = get_settings()
    
    # Get settings from Redis first
    redis_settings = await get_llm_settings_from_redis()
    config = redis_settings or _config_override
    
    model = config.get("model", settings.llm.default_llm_model)
    temperature = config.get("temperature", settings.llm.default_llm_temperature)
    max_tokens = config.get("max_tokens", settings.llm.default_llm_max_tokens)
    
    try:
        client = LLMClient(
            model=model,
            temperature=temperature,
            max_tokens=min(max_tokens, 100),  # Limit for test
        )
        
        result = await client.chat([
            {"role": "user", "content": "Say 'Hello' in one word."}
        ])
        
        return {
            "success": True,
            "model": model,
            "response": result.content,
            "tokens_used": result.tokens_used,
        }
    except Exception as e:
        logger.error("LLM test failed", error=str(e), model=model)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"LLM test failed: {str(e)}",
        )


async def get_current_llm_config_async() -> dict[str, Any]:
    """Get the current LLM config from Redis for use by workers."""
    settings = get_settings()
    redis_settings = await get_llm_settings_from_redis()
    config = redis_settings or {}
    return {
        "model": config.get("model", settings.llm.default_llm_model),
        "temperature": config.get("temperature", settings.llm.default_llm_temperature),
        "max_tokens": config.get("max_tokens", settings.llm.default_llm_max_tokens),
    }


def get_current_llm_config() -> dict[str, Any]:
    """Get the current LLM config for use by other modules (sync version, in-memory only)."""
    settings = get_settings()
    return {
        "model": _config_override.get("model", settings.llm.default_llm_model),
        "temperature": _config_override.get("temperature", settings.llm.default_llm_temperature),
        "max_tokens": _config_override.get("max_tokens", settings.llm.default_llm_max_tokens),
    }


# =============================================================================
# Workflow Settings
# =============================================================================


class WorkflowSettingsResponse(BaseModel):
    """Workflow settings response."""
    max_iterations: int
    

class WorkflowSettingsUpdate(BaseModel):
    """Update workflow settings."""
    max_iterations: int = Field(..., ge=10, le=500, description="Maximum iterations per workflow (10-500)")


@router.get("/workflow")
async def get_workflow_settings() -> WorkflowSettingsResponse:
    """Get current workflow settings."""
    redis_settings = await get_workflow_settings_from_redis()
    return WorkflowSettingsResponse(
        max_iterations=redis_settings.get("max_iterations", DEFAULT_MAX_ITERATIONS) if redis_settings else DEFAULT_MAX_ITERATIONS,
    )


@router.put("/workflow")
async def update_workflow_settings(config: WorkflowSettingsUpdate) -> WorkflowSettingsResponse:
    """Update workflow settings."""
    new_settings = {
        "max_iterations": config.max_iterations,
    }
    
    await set_workflow_settings_in_redis(new_settings)
    
    logger.info("Workflow settings updated", max_iterations=config.max_iterations)
    
    return await get_workflow_settings()


async def get_max_iterations() -> int:
    """Get max iterations setting from Redis for use by workers."""
    redis_settings = await get_workflow_settings_from_redis()
    if redis_settings:
        return redis_settings.get("max_iterations", DEFAULT_MAX_ITERATIONS)
    return DEFAULT_MAX_ITERATIONS
