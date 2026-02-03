# =============================================================================
# SDLC Agent - LLM Client Service
# =============================================================================
# Unified LLM client supporting OpenAI, Azure OpenAI, and Anthropic.
# =============================================================================

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from anthropic import AsyncAnthropic
from openai import AsyncAzureOpenAI, AsyncOpenAI

from sdlc_agent.core.config import LLMProvider, get_settings
from sdlc_agent.core.logging import get_logger

logger = get_logger(__name__)

settings = get_settings()


@dataclass
class LLMResponse:
    """Response from LLM call."""
    
    content: str | None
    tool_calls: list[dict[str, Any]] | None
    finish_reason: str
    tokens_used: int
    model: str


@dataclass
class ToolCall:
    """Parsed tool call from LLM."""
    
    id: str
    name: str
    arguments: dict[str, Any]


class LLMClient:
    """
    Unified LLM client for agent interactions.
    
    Supports OpenAI, Azure OpenAI, and Anthropic providers.
    """
    
    def __init__(
        self,
        provider: LLMProvider | None = None,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ):
        self.provider = provider or settings.llm.default_llm_provider
        self.model = model or settings.llm.default_llm_model
        self.temperature = temperature if temperature is not None else settings.llm.default_llm_temperature
        self.max_tokens = max_tokens or settings.llm.default_llm_max_tokens
        self._client: AsyncOpenAI | AsyncAzureOpenAI | None = None
        self._anthropic_client: AsyncAnthropic | None = None
    
    def _get_client(self) -> AsyncOpenAI | AsyncAzureOpenAI:
        """Get or create the OpenAI/Azure client."""
        if self._client is not None:
            return self._client
        
        if self.provider == LLMProvider.AZURE:
            self._client = AsyncAzureOpenAI(
                api_key=settings.llm.azure_openai_api_key.get_secret_value(),
                azure_endpoint=settings.llm.azure_openai_endpoint,
                api_version=settings.llm.azure_openai_api_version,
                timeout=settings.llm.llm_request_timeout_seconds,
            )
        elif self.provider == LLMProvider.OPENAI:
            self._client = AsyncOpenAI(
                api_key=settings.llm.openai_api_key.get_secret_value(),
                organization=settings.llm.openai_org_id,
                timeout=settings.llm.llm_request_timeout_seconds,
            )
        else:
            raise ValueError(f"Unsupported provider for OpenAI client: {self.provider}")
        
        return self._client
    
    def _get_anthropic_client(self) -> AsyncAnthropic:
        """Get or create the Anthropic client (via Azure proxy)."""
        if self._anthropic_client is not None:
            return self._anthropic_client
        
        api_key = settings.llm.azure_openai_api_key.get_secret_value()
        base_url = f"{settings.llm.azure_openai_endpoint}/anthropic"
        
        self._anthropic_client = AsyncAnthropic(
            api_key=api_key,
            base_url=base_url,
            default_headers={"api-key": api_key},
            timeout=settings.llm.llm_request_timeout_seconds,
        )
        return self._anthropic_client
    
    def _is_anthropic_model(self) -> bool:
        """Check if current model is an Anthropic model."""
        return self.model.startswith("anthropic.") or self.model.startswith("claude-")
    
    async def _chat_anthropic(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> LLMResponse:
        """Handle chat for Anthropic models via proxy."""
        client = self._get_anthropic_client()
        
        # Extract system message if present
        system_prompt = None
        chat_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_prompt = msg["content"]
            else:
                chat_messages.append(msg)
        
        logger.debug(
            "Anthropic LLM request",
            model=self.model,
            message_count=len(chat_messages),
            has_system=bool(system_prompt),
            has_tools=bool(tools),
        )
        
        try:
            kwargs: dict[str, Any] = {
                "model": self.model,
                "messages": chat_messages,
                "max_tokens": self.max_tokens,
            }
            if system_prompt:
                kwargs["system"] = system_prompt
            if self.temperature is not None:
                kwargs["temperature"] = self.temperature
            if tools:
                # Convert OpenAI tool format to Anthropic format
                anthropic_tools = []
                for tool in tools:
                    if tool.get("type") == "function":
                        func = tool["function"]
                        anthropic_tools.append({
                            "name": func["name"],
                            "description": func.get("description", ""),
                            "input_schema": func.get("parameters", {}),
                        })
                kwargs["tools"] = anthropic_tools
            
            response = await client.messages.create(**kwargs)
            
            # Parse response
            content = None
            tool_calls = None
            
            for block in response.content:
                if block.type == "text":
                    content = block.text
                elif block.type == "tool_use":
                    if tool_calls is None:
                        tool_calls = []
                    tool_calls.append({
                        "id": block.id,
                        "type": "function",
                        "function": {
                            "name": block.name,
                            "arguments": json.dumps(block.input),
                        },
                    })
            
            tokens_used = (response.usage.input_tokens + response.usage.output_tokens) if response.usage else 0
            
            logger.info(
                "Anthropic LLM response",
                model=response.model,
                finish_reason=response.stop_reason,
                tokens_used=tokens_used,
                has_tool_calls=bool(tool_calls),
            )
            
            return LLMResponse(
                content=content,
                tool_calls=tool_calls,
                finish_reason=response.stop_reason or "stop",
                tokens_used=tokens_used,
                model=response.model,
            )
            
        except Exception as e:
            logger.error("Anthropic LLM request failed", error=str(e), model=self.model)
            raise
    
    async def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str | dict[str, Any] | None = None,
    ) -> LLMResponse:
        """
        Send a chat completion request.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            tools: Optional list of tool definitions
            tool_choice: Optional tool choice ('auto', 'none', or specific tool)
        
        Returns:
            LLMResponse with content and/or tool calls
        """
        # Route to Anthropic handler if using Anthropic model
        if self._is_anthropic_model():
            return await self._chat_anthropic(messages, tools)
        
        client = self._get_client()
        
        # GPT-5 and newer models use max_completion_tokens instead of max_tokens
        uses_completion_tokens = self.model.startswith("gpt-5") or self.model.startswith("o1") or self.model.startswith("o3")
        
        # o-series and GPT-5 models don't support custom temperature (only default 1)
        supports_custom_temperature = not (self.model.startswith("o1") or self.model.startswith("o3") or self.model.startswith("gpt-5"))
        
        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
        }
        
        # Only set temperature for models that support it
        if supports_custom_temperature:
            kwargs["temperature"] = self.temperature
        
        if uses_completion_tokens:
            kwargs["max_completion_tokens"] = self.max_tokens
        else:
            kwargs["max_tokens"] = self.max_tokens
        
        if tools:
            kwargs["tools"] = tools
            if tool_choice:
                kwargs["tool_choice"] = tool_choice
        
        logger.debug(
            "LLM request",
            model=self.model,
            provider=self.provider.value,
            message_count=len(messages),
            has_tools=bool(tools),
        )
        
        try:
            response = await client.chat.completions.create(**kwargs)
            
            message = response.choices[0].message
            finish_reason = response.choices[0].finish_reason
            
            # Parse tool calls if present
            tool_calls = None
            if message.tool_calls:
                tool_calls = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in message.tool_calls
                ]
            
            tokens_used = response.usage.total_tokens if response.usage else 0
            
            logger.info(
                "LLM response",
                model=response.model,
                finish_reason=finish_reason,
                tokens_used=tokens_used,
                has_tool_calls=bool(tool_calls),
            )
            
            return LLMResponse(
                content=message.content,
                tool_calls=tool_calls,
                finish_reason=finish_reason,
                tokens_used=tokens_used,
                model=response.model,
            )
            
        except Exception as e:
            logger.error("LLM request failed", error=str(e), model=self.model)
            raise
    
    def parse_tool_calls(self, tool_calls: list[dict[str, Any]]) -> list[ToolCall]:
        """Parse tool calls from LLM response."""
        parsed = []
        for tc in tool_calls:
            try:
                args = json.loads(tc["function"]["arguments"])
            except json.JSONDecodeError:
                args = {}
            
            parsed.append(ToolCall(
                id=tc["id"],
                name=tc["function"]["name"],
                arguments=args,
            ))
        return parsed


# Redis key for LLM settings (same as settings.py)
LLM_SETTINGS_KEY = "sdlc:settings:llm"


async def get_llm_settings_from_redis() -> dict[str, Any] | None:
    """Get LLM settings from Redis."""
    import redis.asyncio as aioredis
    try:
        client = aioredis.from_url(str(settings.redis.url))
        data = await client.get(LLM_SETTINGS_KEY)
        await client.aclose()
        if data:
            return json.loads(data)
    except Exception as e:
        logger.warning("Failed to get LLM settings from Redis", error=str(e))
    return None


async def get_llm_client_async() -> LLMClient:
    """Get an LLM client with settings from Redis."""
    redis_settings = await get_llm_settings_from_redis()
    
    if redis_settings:
        model = redis_settings.get("model", settings.llm.default_llm_model)
        temperature = redis_settings.get("temperature", settings.llm.default_llm_temperature)
        max_tokens = redis_settings.get("max_tokens", settings.llm.default_llm_max_tokens)
        
        # Determine provider from model
        if model.startswith("anthropic.") or model.startswith("claude-"):
            provider = LLMProvider.ANTHROPIC
        elif "gpt" in model.lower():
            provider = LLMProvider.AZURE  # Default to Azure for GPT models
        else:
            provider = settings.llm.default_llm_provider
        
        logger.info("Creating LLM client from Redis settings", model=model, provider=provider.value)
        return LLMClient(provider=provider, model=model, temperature=temperature, max_tokens=max_tokens)
    
    # Fallback to default settings
    return LLMClient()


def get_llm_client() -> LLMClient:
    """Get the LLM client instance (sync version, uses env defaults)."""
    return LLMClient()


# Re-export workflow executor functions
from sdlc_agent.services.workflow_executor import (
    enqueue_workflow,
    execute_workflow,
)

__all__ = [
    "LLMClient",
    "LLMResponse",
    "ToolCall",
    "get_llm_client",
    "get_llm_client_async",
    "get_llm_settings_from_redis",
    "enqueue_workflow",
    "execute_workflow",
]
