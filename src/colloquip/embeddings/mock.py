"""Mock embedding provider for deterministic testing.

Uses a hash-based approach so the same text always produces the same vector.
Vectors are normalized to unit length for valid cosine similarity.
"""

import hashlib
import math
from typing import List

from colloquip.embeddings.interface import EmbeddingProvider


class MockEmbeddingProvider(EmbeddingProvider):
    """Deterministic hash-based embedding provider for testing.

    Properties:
    - Same text always produces the same vector (deterministic)
    - Different texts produce different vectors (collision-resistant)
    - Vectors are unit-normalized (valid for cosine similarity)
    - Similar texts (shared word overlap) produce somewhat similar vectors
    """

    def __init__(self, dimension: int = 1536):
        super().__init__(dimension=dimension)

    async def embed(self, text: str) -> List[float]:
        """Generate a deterministic embedding from text.

        Strategy: Hash individual words and combine them to create a
        vector that captures word-level overlap between texts.
        """
        words = text.lower().split()
        vector = [0.0] * self.dimension

        # Accumulate hash-derived values for each word
        for word in words:
            word_hash = hashlib.sha256(word.encode()).digest()
            for i in range(self.dimension):
                byte_idx = i % len(word_hash)
                # Map byte to [-1, 1] range
                val = (word_hash[byte_idx] / 127.5) - 1.0
                # Use position-dependent mixing to spread influence
                mix_hash = hashlib.md5(f"{word}:{i}".encode()).digest()
                mix_val = (mix_hash[0] / 127.5) - 1.0
                vector[i] += val * 0.7 + mix_val * 0.3

        # Normalize to unit length
        norm = math.sqrt(sum(v * v for v in vector))
        if norm > 0:
            vector = [v / norm for v in vector]
        else:
            # Empty text: return a fixed unit vector
            vector = [0.0] * self.dimension
            vector[0] = 1.0

        return vector
