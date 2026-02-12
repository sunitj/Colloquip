"""Abstract base class for embedding providers."""

import math
from abc import ABC, abstractmethod
from typing import List


def cosine_similarity(a: List[float], b: List[float]) -> float:
    """Compute cosine similarity between two vectors.

    Returns a value between -1.0 and 1.0. Returns 0.0 for zero-length vectors.
    """
    if len(a) != len(b):
        raise ValueError(f"Vector dimension mismatch: {len(a)} vs {len(b)}")

    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))

    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0

    return dot / (norm_a * norm_b)


class EmbeddingProvider(ABC):
    """Abstract base class for text embedding providers.

    Implementations must produce vectors of the configured dimension.
    """

    def __init__(self, dimension: int = 1536):
        self.dimension = dimension

    @abstractmethod
    async def embed(self, text: str) -> List[float]:
        """Embed a single text string into a vector."""
        ...

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Embed multiple texts. Default implementation calls embed() sequentially.

        Subclasses should override for batch-optimized implementations.
        """
        return [await self.embed(text) for text in texts]
