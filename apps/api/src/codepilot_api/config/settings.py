"""Typed, environment-based application settings."""

from __future__ import annotations

from enum import StrEnum
from functools import lru_cache
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_DEVELOPMENT_JWT_SECRET = "development-only-secret-change-before-production-32-chars"


class AppEnvironment(StrEnum):
    """Supported runtime environments."""

    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"


class AiProvider(StrEnum):
    """Supported providers for generation and repository embeddings."""

    OPENAI = "openai"
    GEMINI = "gemini"
    OLLAMA = "ollama"


class Settings(BaseSettings):
    """Configuration loaded from environment variables and an optional .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "CodePilot AI API"
    app_version: str = "0.1.0"
    app_env: AppEnvironment = AppEnvironment.DEVELOPMENT
    debug: bool = False
    api_v1_prefix: str = "/api/v1"
    log_level: str = "INFO"
    database_url: str = "postgresql+asyncpg://codepilot:codepilot@localhost:5432/codepilot"
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])
    trusted_hosts: list[str] = Field(default_factory=lambda: ["localhost", "127.0.0.1"])
    jwt_secret_key: SecretStr = SecretStr(DEFAULT_DEVELOPMENT_JWT_SECRET)
    jwt_algorithm: str = "HS256"
    ai_provider: AiProvider = AiProvider.OPENAI
    openai_api_key: SecretStr | None = None
    openai_project_summary_model: str = "gpt-5"
    openai_repository_chat_model: str = "gpt-5"
    openai_embedding_model: str = "text-embedding-3-small"
    openai_timeout_seconds: int = Field(default=90, ge=10, le=600)
    gemini_api_key: SecretStr | None = None
    # Gemini 2.5 Flash is a stable, low-latency model with structured-output support.
    gemini_generation_model: str = "gemini-2.5-flash"
    gemini_embedding_model: str = "gemini-embedding-001"
    gemini_embedding_dimensions: int = Field(default=768, ge=128, le=3072)
    gemini_timeout_seconds: int = Field(default=120, ge=10, le=600)
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_chat_model: str = "qwen2.5-coder:3b"
    ollama_embedding_model: str = "nomic-embed-text"
    ollama_timeout_seconds: int = Field(default=300, ge=10, le=900)
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: SecretStr | None = None
    qdrant_collection_name: str = "codepilot_repository_chunks"
    repository_rag_chunk_characters: int = Field(default=2_000, ge=500, le=8_000)
    repository_rag_chunk_overlap_lines: int = Field(default=12, ge=0, le=100)
    repository_rag_max_file_bytes: int = Field(default=512 * 1024, ge=4 * 1024, le=4 * 1024 * 1024)
    repository_rag_max_chunks: int = Field(default=10_000, ge=10, le=100_000)
    repository_rag_search_limit: int = Field(default=6, ge=1, le=12)
    repository_rag_min_score: float = Field(default=0.2, ge=-1.0, le=1.0)
    access_token_expire_minutes: int = Field(default=15, ge=1, le=60)
    refresh_token_expire_days: int = Field(default=30, ge=1, le=90)
    refresh_cookie_name: str = "codepilot_refresh"
    repository_storage_root: Path = Path("data/repositories")
    repository_upload_max_bytes: int = Field(default=100 * 1024 * 1024, ge=1)
    repository_extracted_max_bytes: int = Field(default=500 * 1024 * 1024, ge=1)
    repository_max_files: int = Field(default=50_000, ge=1)
    repository_max_compression_ratio: int = Field(default=100, ge=1)
    git_clone_timeout_seconds: int = Field(default=120, ge=10, le=600)
    repository_analysis_max_file_bytes: int = Field(default=2 * 1024 * 1024, ge=64 * 1024)
    repository_analysis_max_symbols: int = Field(default=10_000, ge=100, le=50_000)
    repository_analysis_max_folders: int = Field(default=500, ge=10, le=5_000)

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, value: str) -> str:
        """Allow supported SQLAlchemy async schemes and normalize Railway's Postgres URL."""
        scheme = urlparse(value).scheme
        if scheme in {"postgres", "postgresql"}:
            return f"postgresql+asyncpg://{value.split('://', maxsplit=1)[1]}"
        if scheme not in {"postgresql+asyncpg", "sqlite+aiosqlite"}:
            message = "DATABASE_URL must use postgresql+asyncpg or sqlite+aiosqlite."
            raise ValueError(message)
        return value

    @field_validator("cors_origins", "trusted_hosts", mode="before")
    @classmethod
    def parse_list(cls, value: Any) -> Any:
        """Accept JSON lists from environment variables and native Python lists in tests."""
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @model_validator(mode="after")
    def validate_production_secrets(self) -> Settings:
        """Prevent startup with a weak development JWT secret in production."""
        secret = self.jwt_secret_key.get_secret_value()
        if self.is_production and (len(secret) < 32 or secret == DEFAULT_DEVELOPMENT_JWT_SECRET):
            message = (
                "JWT_SECRET_KEY must be a unique secret of at least 32 characters in production."
            )
            raise ValueError(message)
        return self

    @property
    def is_production(self) -> bool:
        """Whether the application is running with production safeguards."""
        return self.app_env == AppEnvironment.PRODUCTION


@lru_cache
def get_settings() -> Settings:
    """Return one immutable settings object per process."""
    return Settings()
