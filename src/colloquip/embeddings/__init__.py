"""Embedding providers for vector similarity search."""

import os

from colloquip.embeddings.interface import EmbeddingProvider
from colloquip.embeddings.mock import MockEmbeddingProvider


def create_embedding_provider(provider: str | None = None) -> EmbeddingProvider:
    """Create an embedding provider based on configuration.

    Args:
        provider: One of "mock" or "openai". Defaults to EMBEDDING_PROVIDER
                  env var, or "mock" if not set.
    """
    provider = provider or os.environ.get("EMBEDDING_PROVIDER", "mock")

    if provider == "mock":
        return MockEmbeddingProvider()
    elif provider == "openai":
        from colloquip.embeddings.openai import OpenAIEmbeddingProvider

        return OpenAIEmbeddingProvider()
    else:
        raise ValueError(f"Unknown embedding provider: {provider}")


__all__ = ["EmbeddingProvider", "MockEmbeddingProvider", "create_embedding_provider"]
