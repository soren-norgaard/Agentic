"""Configuration management for Agentic SDLC."""

from enum import Enum
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings


class LLMProvider(str, Enum):
    """Supported LLM providers."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # LLM Configuration
    llm_provider: LLMProvider = Field(default=LLMProvider.OPENAI)
    llm_model: str = Field(default="gpt-4o")
    openai_api_key: str | None = Field(default=None)
    anthropic_api_key: str | None = Field(default=None)

    # Temperature settings per agent type
    planning_temperature: float = Field(default=0.7)
    coding_temperature: float = Field(default=0.2)
    review_temperature: float = Field(default=0.3)

    # Logging
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(default="INFO")

    # Human-in-the-loop
    require_human_approval: bool = Field(default=True)
    approval_timeout_seconds: int = Field(default=300)

    # Memory and persistence
    memory_backend: Literal["local", "redis", "postgres"] = Field(default="local")
    checkpoint_dir: Path = Field(default=Path("./checkpoints"))

    # Execution limits
    max_iterations: int = Field(default=50)
    max_retries: int = Field(default=3)

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    def get_llm_api_key(self) -> str:
        """Get the API key for the configured LLM provider."""
        if self.llm_provider == LLMProvider.OPENAI:
            if not self.openai_api_key:
                raise ValueError("OPENAI_API_KEY is required when using OpenAI provider")
            return self.openai_api_key
        elif self.llm_provider == LLMProvider.ANTHROPIC:
            if not self.anthropic_api_key:
                raise ValueError("ANTHROPIC_API_KEY is required when using Anthropic provider")
            return self.anthropic_api_key
        raise ValueError(f"Unknown LLM provider: {self.llm_provider}")


# Global settings instance
settings = Settings()
