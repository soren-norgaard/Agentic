# =============================================================================
# SDLC Agent - Configuration Management
# =============================================================================
# Pydantic-based configuration with validation, type safety, and environment
# variable support. All configuration is validated at startup.
# =============================================================================

from __future__ import annotations

import secrets
from enum import Enum
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import (
    AnyHttpUrl,
    Field,
    PostgresDsn,
    RedisDsn,
    SecretStr,
    field_validator,
    model_validator,
)
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(str, Enum):
    """Application environment types."""

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class LogLevel(str, Enum):
    """Logging levels."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LLMProvider(str, Enum):
    """Supported LLM providers."""

    OPENAI = "openai"
    AZURE = "azure"
    ANTHROPIC = "anthropic"


class AppSettings(BaseSettings):
    """Core application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = Field(default="sdlc-agent", description="Application name")
    app_env: Environment = Field(
        default=Environment.DEVELOPMENT, description="Application environment"
    )
    debug: bool = Field(default=False, description="Debug mode")
    log_level: LogLevel = Field(default=LogLevel.INFO, description="Logging level")
    secret_key: SecretStr = Field(
        default_factory=lambda: SecretStr(secrets.token_urlsafe(32)),
        description="Secret key for signing",
    )

    @field_validator("secret_key")
    @classmethod
    def validate_secret_key(cls, v: SecretStr) -> SecretStr:
        """Ensure secret key is sufficiently long."""
        if len(v.get_secret_value()) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters")
        return v

    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.app_env == Environment.DEVELOPMENT

    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.app_env == Environment.PRODUCTION


class APISettings(BaseSettings):
    """API server settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="API_",
        case_sensitive=False,
        extra="ignore",
    )

    host: str = Field(default="0.0.0.0", description="API host")
    port: int = Field(default=8000, ge=1, le=65535, description="API port")
    version: str = Field(default="v1", description="API version")
    rate_limit_requests: int = Field(
        default=100, ge=1, description="Rate limit requests per window"
    )
    rate_limit_window_seconds: int = Field(
        default=60, ge=1, description="Rate limit window in seconds"
    )
    cors_origins: list[str] = Field(
        default=["http://localhost:3000"], description="Allowed CORS origins"
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: Any) -> list[str]:
        """Parse CORS origins from string or list."""
        if isinstance(v, str):
            import json

            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return [origin.strip() for origin in v.split(",")]
        return v


class DatabaseSettings(BaseSettings):
    """Database connection settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="DATABASE_",
        case_sensitive=False,
        extra="ignore",
    )

    url: PostgresDsn = Field(
        default="postgresql+asyncpg://sdlc:sdlc_password@localhost:5432/sdlc_agent",
        description="Database connection URL",
    )
    pool_size: int = Field(default=20, ge=1, le=100, description="Connection pool size")
    max_overflow: int = Field(
        default=10, ge=0, le=50, description="Max overflow connections"
    )
    echo: bool = Field(default=False, description="Echo SQL queries")

    @property
    def async_url(self) -> str:
        """Get async database URL."""
        url_str = str(self.url)
        if "postgresql://" in url_str and "+asyncpg" not in url_str:
            return url_str.replace("postgresql://", "postgresql+asyncpg://")
        return url_str


class RedisSettings(BaseSettings):
    """Redis connection settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="REDIS_",
        case_sensitive=False,
        extra="ignore",
    )

    url: RedisDsn = Field(
        default="redis://localhost:6379/0", description="Redis connection URL"
    )
    password: SecretStr | None = Field(default=None, description="Redis password")
    max_connections: int = Field(
        default=50, ge=1, le=200, description="Max connections"
    )


class LLMSettings(BaseSettings):
    """LLM provider settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
    )

    # Provider selection
    default_llm_provider: LLMProvider = Field(
        default=LLMProvider.ANTHROPIC, description="Default LLM provider"
    )
    default_llm_model: str = Field(
        default="anthropic.claude-sonnet-4-5-20250929-v1:0", description="Default LLM model"
    )
    default_llm_temperature: float = Field(
        default=0.1, ge=0.0, le=2.0, description="Default temperature"
    )
    default_llm_max_tokens: int = Field(
        default=4096, ge=1, le=128000, description="Default max tokens"
    )
    llm_request_timeout_seconds: int = Field(
        default=120, ge=1, description="Request timeout"
    )

    # OpenAI
    openai_api_key: SecretStr | None = Field(default=None, description="OpenAI API key")
    openai_org_id: str | None = Field(default=None, description="OpenAI organization ID")

    # Azure OpenAI
    azure_openai_api_key: SecretStr | None = Field(
        default=None, description="Azure OpenAI API key"
    )
    azure_openai_endpoint: str | None = Field(
        default=None, description="Azure OpenAI endpoint"
    )
    azure_openai_api_version: str = Field(
        default="2024-02-15-preview", description="Azure API version"
    )

    # Anthropic
    anthropic_api_key: SecretStr | None = Field(
        default=None, description="Anthropic API key"
    )

    @field_validator("azure_openai_endpoint", mode="before")
    @classmethod
    def parse_azure_endpoint(cls, v: Any) -> str | None:
        """Handle empty string as None for Azure endpoint."""
        if v == "" or v is None:
            return None
        return v

    @model_validator(mode="after")
    def validate_provider_keys(self) -> "LLMSettings":
        """Ensure the selected provider has required credentials."""
        provider = self.default_llm_provider
        if provider == LLMProvider.OPENAI and not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required when using OpenAI provider")
        if provider == LLMProvider.AZURE:
            if not self.azure_openai_api_key or not self.azure_openai_endpoint:
                raise ValueError(
                    "AZURE_OPENAI_API_KEY and AZURE_OPENAI_ENDPOINT are required"
                )
        if provider == LLMProvider.ANTHROPIC and not self.anthropic_api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY is required when using Anthropic provider"
            )
        return self


class VectorDBSettings(BaseSettings):
    """Vector database settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="QDRANT_",
        case_sensitive=False,
        extra="ignore",
    )

    url: AnyHttpUrl = Field(
        default="http://localhost:6333", description="Qdrant URL"
    )
    api_key: SecretStr | None = Field(default=None, description="Qdrant API key")
    collection_name: str = Field(
        default="sdlc_memory", description="Default collection name"
    )


class StorageSettings(BaseSettings):
    """Object storage settings (S3/MinIO)."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="S3_",
        case_sensitive=False,
        extra="ignore",
    )

    endpoint_url: AnyHttpUrl = Field(
        default="http://localhost:9000", description="S3 endpoint URL"
    )
    access_key: SecretStr = Field(
        default=SecretStr("minioadmin"), description="S3 access key"
    )
    secret_key: SecretStr = Field(
        default=SecretStr("minioadmin"), description="S3 secret key"
    )
    bucket_name: str = Field(default="sdlc-artifacts", description="Default bucket")
    region: str = Field(default="us-east-1", description="S3 region")


class AuthSettings(BaseSettings):
    """Authentication and authorization settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
    )

    auth_enabled: bool = Field(default=True, description="Enable authentication")
    auth_api_key_header: str = Field(
        default="X-API-Key", description="API key header name"
    )
    jwt_secret_key: SecretStr = Field(
        default_factory=lambda: SecretStr(secrets.token_urlsafe(32)),
        description="JWT secret key",
    )
    jwt_algorithm: str = Field(default="HS256", description="JWT algorithm")
    jwt_access_token_expire_minutes: int = Field(
        default=30, ge=1, description="Access token expiry"
    )
    jwt_refresh_token_expire_days: int = Field(
        default=7, ge=1, description="Refresh token expiry"
    )

    # OAuth2 (optional)
    oauth2_enabled: bool = Field(default=False, description="Enable OAuth2")
    oauth2_provider: str | None = Field(default=None, description="OAuth2 provider")
    oauth2_client_id: str | None = Field(default=None, description="OAuth2 client ID")
    oauth2_client_secret: SecretStr | None = Field(
        default=None, description="OAuth2 client secret"
    )
    oauth2_issuer_url: str | None = Field(
        default=None, description="OAuth2 issuer URL"
    )

    @field_validator("oauth2_issuer_url", mode="before")
    @classmethod
    def parse_oauth2_url(cls, v: Any) -> str | None:
        """Handle empty string as None for OAuth2 URL."""
        if v == "" or v is None:
            return None
        return v


class ObservabilitySettings(BaseSettings):
    """Observability and monitoring settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="OTEL_",
        case_sensitive=False,
        extra="ignore",
    )

    enabled: bool = Field(default=True, description="Enable OpenTelemetry")
    service_name: str = Field(default="sdlc-agent", description="Service name")
    exporter_otlp_endpoint: str = Field(
        default="http://localhost:4317", description="OTLP endpoint"
    )
    exporter_otlp_protocol: str = Field(default="grpc", description="OTLP protocol")

    # Sentry
    sentry_dsn: str | None = Field(default=None, alias="SENTRY_DSN")
    sentry_environment: str = Field(
        default="development", alias="SENTRY_ENVIRONMENT"
    )
    sentry_traces_sample_rate: float = Field(
        default=0.1, ge=0.0, le=1.0, alias="SENTRY_TRACES_SAMPLE_RATE"
    )


class GitHubSettings(BaseSettings):
    """GitHub integration settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="GITHUB_",
        case_sensitive=False,
        extra="ignore",
    )

    token: SecretStr | None = Field(
        default=None, description="GitHub Personal Access Token"
    )
    owner: str = Field(default="", description="GitHub repository owner")
    repo: str = Field(default="", description="GitHub repository name")
    app_id: int | None = Field(default=None, description="GitHub App ID")
    app_private_key: SecretStr | None = Field(
        default=None, description="GitHub App private key"
    )
    webhook_secret: SecretStr | None = Field(
        default=None, description="GitHub webhook secret"
    )
    auto_sync_enabled: bool = Field(
        default=False, description="Auto-sync tasks to GitHub Issues"
    )

    @field_validator("app_id", mode="before")
    @classmethod
    def empty_string_to_none(cls, v: Any) -> int | None:
        """Convert empty strings to None for optional int fields."""
        if v == "" or v is None:
            return None
        return int(v)

    @property
    def is_configured(self) -> bool:
        """Check if GitHub integration is properly configured."""
        return bool(self.token and self.owner and self.repo)


class AgentSettings(BaseSettings):
    """Agent execution settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="AGENT_",
        case_sensitive=False,
        extra="ignore",
    )

    max_iterations: int = Field(
        default=50, ge=1, le=1000, description="Max agent iterations"
    )
    timeout_seconds: int = Field(
        default=300, ge=1, description="Agent execution timeout"
    )
    checkpoint_enabled: bool = Field(
        default=True, description="Enable checkpointing"
    )
    human_in_loop_enabled: bool = Field(
        default=True, description="Enable human-in-the-loop"
    )


class Settings(BaseSettings):
    """Root settings container aggregating all configuration sections."""

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
    )

    app: AppSettings = Field(default_factory=AppSettings)
    api: APISettings = Field(default_factory=APISettings)
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    llm: LLMSettings = Field(default_factory=LLMSettings)
    vector_db: VectorDBSettings = Field(default_factory=VectorDBSettings)
    storage: StorageSettings = Field(default_factory=StorageSettings)
    auth: AuthSettings = Field(default_factory=AuthSettings)
    observability: ObservabilitySettings = Field(default_factory=ObservabilitySettings)
    agent: AgentSettings = Field(default_factory=AgentSettings)
    github: GitHubSettings = Field(default_factory=GitHubSettings)

    # Paths
    base_dir: Path = Field(
        default_factory=lambda: Path(__file__).resolve().parent.parent.parent.parent
    )

    @property
    def artifacts_dir(self) -> Path:
        """Get artifacts directory path."""
        path = self.base_dir / "artifacts"
        path.mkdir(parents=True, exist_ok=True)
        return path


@lru_cache
def get_settings() -> Settings:
    """
    Get cached application settings.

    Returns:
        Settings: Application settings singleton
    """
    return Settings()
