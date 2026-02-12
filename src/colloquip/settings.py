"""Application settings with environment variable validation.

Uses pydantic BaseModel with env var loading for typed, validated configuration.
All settings have sensible defaults for development.
"""

import os
from typing import List, Optional

from pydantic import BaseModel, Field


class DatabaseSettings(BaseModel):
    url: str = "sqlite+aiosqlite:///colloquip.db"
    pool_size: int = 5
    max_overflow: int = 10


class LLMSettings(BaseModel):
    provider: str = "anthropic"
    model: str = "claude-sonnet-4-5-20250929"
    max_tokens: int = 2048
    temperature: float = 0.7


class EmbeddingSettings(BaseModel):
    provider: str = "mock"  # mock | openai
    model: str = "text-embedding-3-small"
    dimension: int = 1536


class MemorySettings(BaseModel):
    store: str = "in_memory"  # in_memory | pgvector
    similarity_threshold: float = 0.75
    max_results: int = 3


class WatcherSettings(BaseModel):
    poll_interval: int = 300  # seconds
    max_auto_threads_per_hour: int = 5
    redis_url: str = "redis://localhost:6379"


class DeploymentSettings(BaseModel):
    environment: str = "development"  # development | staging | production
    log_level: str = "INFO"
    log_format: str = "text"  # text | json
    cors_origins: List[str] = Field(default_factory=lambda: ["*"])
    max_cost_per_thread_usd: float = 5.0
    monthly_budget_usd: float = 500.0


class Settings(BaseModel):
    """Top-level application settings.

    Loaded from environment variables at startup.
    """

    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    llm: LLMSettings = Field(default_factory=LLMSettings)
    embedding: EmbeddingSettings = Field(default_factory=EmbeddingSettings)
    memory: MemorySettings = Field(default_factory=MemorySettings)
    watchers: WatcherSettings = Field(default_factory=WatcherSettings)
    deployment: DeploymentSettings = Field(default_factory=DeploymentSettings)


def load_settings() -> Settings:
    """Load settings from environment variables."""
    database = DatabaseSettings(
        url=os.environ.get("DATABASE_URL", "sqlite+aiosqlite:///colloquip.db"),
    )

    embedding = EmbeddingSettings(
        provider=os.environ.get("EMBEDDING_PROVIDER", "mock"),
    )

    memory = MemorySettings(
        store=os.environ.get("MEMORY_STORE", "in_memory"),
    )

    watchers = WatcherSettings(
        poll_interval=int(os.environ.get("WATCHER_POLL_INTERVAL", "300")),
        redis_url=os.environ.get("REDIS_URL", "redis://localhost:6379"),
    )

    cors_origins_str = os.environ.get("CORS_ORIGINS", "*")
    cors_origins = [o.strip() for o in cors_origins_str.split(",")]

    deployment = DeploymentSettings(
        environment=os.environ.get("ENVIRONMENT", "development"),
        log_level=os.environ.get("LOG_LEVEL", "INFO"),
        log_format=os.environ.get("LOG_FORMAT", "text"),
        cors_origins=cors_origins,
        max_cost_per_thread_usd=float(os.environ.get("MAX_COST_PER_THREAD_USD", "5.0")),
        monthly_budget_usd=float(os.environ.get("MONTHLY_BUDGET_USD", "500.0")),
    )

    return Settings(
        database=database,
        embedding=embedding,
        memory=memory,
        watchers=watchers,
        deployment=deployment,
    )
