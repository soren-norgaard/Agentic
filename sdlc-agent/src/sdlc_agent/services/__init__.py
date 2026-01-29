# =============================================================================
# SDLC Agent - LLM Client Service
# =============================================================================
# Unified LLM client supporting OpenAI, Azure OpenAI, and Anthropic.
# =============================================================================

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

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
    
    def _get_client(self) -> AsyncOpenAI | AsyncAzureOpenAI:
        """Get or create the LLM client."""
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
            raise ValueError(f"Unsupported provider: {self.provider}")
        
        return self._client
    
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
        client = self._get_client()
        
        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }
        
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


# Singleton instance
_llm_client: LLMClient | None = None


def get_llm_client() -> LLMClient:
    """Get the singleton LLM client instance."""
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
    return _llm_client


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
    "enqueue_workflow",
    "execute_workflow",
]
