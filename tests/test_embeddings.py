"""Tests for embedding providers."""

import math

import pytest

from colloquip.embeddings.interface import EmbeddingProvider, cosine_similarity
from colloquip.embeddings.mock import MockEmbeddingProvider


# --- cosine_similarity ---


class TestCosineSimilarity:
    def test_identical_vectors(self):
        v = [1.0, 2.0, 3.0]
        assert cosine_similarity(v, v) == pytest.approx(1.0)

    def test_orthogonal_vectors(self):
        a = [1.0, 0.0, 0.0]
        b = [0.0, 1.0, 0.0]
        assert cosine_similarity(a, b) == pytest.approx(0.0)

    def test_opposite_vectors(self):
        a = [1.0, 2.0, 3.0]
        b = [-1.0, -2.0, -3.0]
        assert cosine_similarity(a, b) == pytest.approx(-1.0)

    def test_zero_vector_returns_zero(self):
        a = [0.0, 0.0, 0.0]
        b = [1.0, 2.0, 3.0]
        assert cosine_similarity(a, b) == 0.0
        assert cosine_similarity(b, a) == 0.0

    def test_dimension_mismatch_raises(self):
        a = [1.0, 2.0]
        b = [1.0, 2.0, 3.0]
        with pytest.raises(ValueError, match="dimension mismatch"):
            cosine_similarity(a, b)

    def test_similarity_range(self):
        a = [0.3, -0.7, 0.5, 1.0]
        b = [0.9, 0.2, -0.4, 0.6]
        sim = cosine_similarity(a, b)
        assert -1.0 <= sim <= 1.0

    def test_known_value(self):
        a = [1.0, 0.0]
        b = [1.0, 1.0]
        expected = 1.0 / math.sqrt(2)
        assert cosine_similarity(a, b) == pytest.approx(expected)


# --- MockEmbeddingProvider ---


class TestMockEmbeddingProvider:
    @pytest.fixture
    def provider(self):
        return MockEmbeddingProvider(dimension=64)

    @pytest.mark.asyncio
    async def test_returns_correct_dimension(self, provider):
        vec = await provider.embed("hello world")
        assert len(vec) == 64

    @pytest.mark.asyncio
    async def test_default_dimension(self):
        provider = MockEmbeddingProvider()
        vec = await provider.embed("test")
        assert len(vec) == 1536

    @pytest.mark.asyncio
    async def test_deterministic_same_text(self, provider):
        v1 = await provider.embed("the same text")
        v2 = await provider.embed("the same text")
        assert v1 == v2

    @pytest.mark.asyncio
    async def test_different_texts_different_vectors(self, provider):
        v1 = await provider.embed("apples and oranges")
        v2 = await provider.embed("quantum mechanics")
        assert v1 != v2

    @pytest.mark.asyncio
    async def test_unit_normalized(self, provider):
        vec = await provider.embed("some text for normalization check")
        norm = math.sqrt(sum(v * v for v in vec))
        assert norm == pytest.approx(1.0, abs=1e-6)

    @pytest.mark.asyncio
    async def test_empty_text_returns_valid_vector(self, provider):
        vec = await provider.embed("")
        assert len(vec) == 64
        norm = math.sqrt(sum(v * v for v in vec))
        assert norm == pytest.approx(1.0, abs=1e-6)

    @pytest.mark.asyncio
    async def test_similar_texts_higher_similarity(self, provider):
        """Texts sharing words should have higher similarity than unrelated texts."""
        v_base = await provider.embed("drug target validation biology")
        v_similar = await provider.embed("target validation in drug discovery biology")
        v_unrelated = await provider.embed("quantum computing neural network")

        sim_similar = cosine_similarity(v_base, v_similar)
        sim_unrelated = cosine_similarity(v_base, v_unrelated)

        assert sim_similar > sim_unrelated

    @pytest.mark.asyncio
    async def test_embed_batch(self, provider):
        texts = ["hello", "world", "test"]
        results = await provider.embed_batch(texts)

        assert len(results) == 3
        for vec in results:
            assert len(vec) == 64

        # Each should match individual embed
        for i, text in enumerate(texts):
            individual = await provider.embed(text)
            assert results[i] == individual

    @pytest.mark.asyncio
    async def test_embed_batch_empty(self, provider):
        results = await provider.embed_batch([])
        assert results == []


# --- EmbeddingProvider ABC ---


class TestEmbeddingProviderABC:
    def test_cannot_instantiate_directly(self):
        with pytest.raises(TypeError):
            EmbeddingProvider()

    def test_dimension_stored(self):
        provider = MockEmbeddingProvider(dimension=256)
        assert provider.dimension == 256

    def test_default_dimension(self):
        provider = MockEmbeddingProvider()
        assert provider.dimension == 1536
