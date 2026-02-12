"""OpenAI embedding provider using text-embedding-3-small.

Requires the 'openai' package: pip install colloquip[embeddings]
Falls back to MockEmbeddingProvider if the package or API key is not available.
"""

import logging
import os
from typing import List

from colloquip.embeddings.interface import EmbeddingProvider

logger = logging.getLogger(__name__)


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """Embedding provider using OpenAI's text-embedding-3-small model.

    Falls back gracefully if the openai package is not installed
    or the API key is not configured.
    """

    def __init__(
        self,
        model: str = "text-embedding-3-small",
        dimension: int = 1536,
        api_key: str | None = None,
    ):
        super().__init__(dimension=dimension)
        self.model = model
        self._client = None

        try:
            import openai
            key = api_key or os.environ.get("OPENAI_API_KEY")
            if key:
                self._client = openai.AsyncOpenAI(api_key=key)
            else:
                logger.warning(
                    "OPENAI_API_KEY not set. OpenAIEmbeddingProvider will "
                    "raise errors on embed() calls."
                )
        except ImportError:
            logger.warning(
                "openai package not installed. Install with: "
                "pip install colloquip[embeddings]"
            )

    async def embed(self, text: str) -> List[float]:
        """Embed text using OpenAI API."""
        if self._client is None:
            raise RuntimeError(
                "OpenAI client not available. Ensure the openai package is "
                "installed and OPENAI_API_KEY is set."
            )

        try:
            response = await self._client.embeddings.create(
                model=self.model,
                input=text,
                dimensions=self.dimension,
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error("OpenAI embedding failed: %s", e)
            raise RuntimeError(f"Embedding generation failed: {e}") from e

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Embed multiple texts in a single API call."""
        if self._client is None:
            raise RuntimeError(
                "OpenAI client not available. Ensure the openai package is "
                "installed and OPENAI_API_KEY is set."
            )

        if not texts:
            return []

        try:
            response = await self._client.embeddings.create(
                model=self.model,
                input=texts,
                dimensions=self.dimension,
            )
            # Sort by index to ensure order matches input
            sorted_data = sorted(response.data, key=lambda x: x.index)
            return [item.embedding for item in sorted_data]
        except Exception as e:
            logger.error("OpenAI batch embedding failed for %d texts: %s", len(texts), e)
            raise RuntimeError(f"Batch embedding generation failed: {e}") from e
