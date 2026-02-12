"""Tests for memory annotations and correction propagation."""

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from colloquip.embeddings.mock import MockEmbeddingProvider
from colloquip.memory.retriever import MemoryRetriever, RetrievedMemories
from colloquip.memory.store import InMemoryStore, SynthesisMemory
from colloquip.models import MemoryAnnotationType


SUB_A = uuid4()


def make_memory(topic: str, **kwargs) -> SynthesisMemory:
    defaults = dict(
        thread_id=uuid4(),
        subreddit_id=SUB_A,
        subreddit_name="target_validation",
        topic=topic,
        synthesis_content=f"Synthesis about {topic}",
        key_conclusions=[f"Conclusion about {topic}"],
        confidence_level="high",
        created_at=datetime(2026, 1, 15, tzinfo=timezone.utc),
    )
    defaults.update(kwargs)
    return SynthesisMemory(**defaults)


class TestMemoryAnnotationTypes:
    def test_annotation_type_values(self):
        assert MemoryAnnotationType.OUTDATED == "outdated"
        assert MemoryAnnotationType.CORRECTION == "correction"
        assert MemoryAnnotationType.CONFIRMED == "confirmed"
        assert MemoryAnnotationType.CONTEXT == "context"


class TestInMemoryStoreAnnotations:
    @pytest.fixture
    def store(self):
        return InMemoryStore()

    @pytest.mark.asyncio
    async def test_annotate_memory(self, store):
        mem = make_memory("test topic")
        await store.save(mem)

        await store.annotate(
            memory_id=mem.id,
            annotation_type="correction",
            content="This conclusion was later disproven.",
            created_by="researcher",
        )

        annotations = await store.get_annotations(mem.id)
        assert len(annotations) == 1
        assert annotations[0]["annotation_type"] == "correction"
        assert annotations[0]["content"] == "This conclusion was later disproven."
        assert annotations[0]["created_by"] == "researcher"

    @pytest.mark.asyncio
    async def test_annotate_nonexistent_raises(self, store):
        with pytest.raises(ValueError):
            await store.annotate(uuid4(), "correction", "test")

    @pytest.mark.asyncio
    async def test_multiple_annotations(self, store):
        mem = make_memory("test topic")
        await store.save(mem)

        await store.annotate(mem.id, "confirmed", "Verified by experiment.")
        await store.annotate(mem.id, "context", "Additional background.")

        annotations = await store.get_annotations(mem.id)
        assert len(annotations) == 2

    @pytest.mark.asyncio
    async def test_annotations_empty_for_unannotated(self, store):
        mem = make_memory("test topic")
        await store.save(mem)
        assert await store.get_annotations(mem.id) == []


class TestAnnotationsInRetrieval:
    @pytest.fixture
    def provider(self):
        return MockEmbeddingProvider(dimension=64)

    @pytest.fixture
    def store(self):
        return InMemoryStore()

    @pytest.fixture
    def retriever(self, store, provider):
        return MemoryRetriever(store=store, embedding_provider=provider)

    @pytest.mark.asyncio
    async def test_retriever_includes_annotations(self, retriever, store, provider):
        emb = await provider.embed("drug target biology")
        mem = make_memory("drug target", embedding=emb)
        await store.save(mem)
        await store.annotate(mem.id, "correction", "IC50 was revised to 10nM")

        result = await retriever.retrieve("drug target", subreddit_id=SUB_A)
        assert len(result.arena) == 1
        assert str(mem.id) in result.annotations
        assert result.annotations[str(mem.id)][0]["content"] == "IC50 was revised to 10nM"

    @pytest.mark.asyncio
    async def test_retriever_no_annotations(self, retriever, store, provider):
        emb = await provider.embed("drug target biology")
        mem = make_memory("drug target", embedding=emb)
        await store.save(mem)

        result = await retriever.retrieve("drug target", subreddit_id=SUB_A)
        assert result.annotations == {}


class TestAnnotationsInFormatting:
    def test_outdated_annotation_shows_warning(self):
        mem = make_memory("Old finding", key_conclusions=["X is true"])
        memories = RetrievedMemories(
            arena=[mem],
            annotations={str(mem.id): [
                {"annotation_type": "outdated", "content": "Superseded by new data."}
            ]},
        )
        text = memories.format_for_prompt()
        assert "WARNING - OUTDATED" in text
        assert "Superseded by new data" in text

    def test_correction_annotation_shows_correction(self):
        mem = make_memory("Finding", key_conclusions=["Y is true"])
        memories = RetrievedMemories(
            arena=[mem],
            annotations={str(mem.id): [
                {"annotation_type": "correction", "content": "Y is actually Z."}
            ]},
        )
        text = memories.format_for_prompt()
        assert "Human correction" in text
        assert "Y is actually Z" in text

    def test_context_annotation(self):
        mem = make_memory("Finding")
        memories = RetrievedMemories(
            arena=[mem],
            annotations={str(mem.id): [
                {"annotation_type": "context", "content": "Study was in mice."}
            ]},
        )
        text = memories.format_for_prompt()
        assert "Additional context" in text
        assert "Study was in mice" in text

    def test_confirmed_annotation_not_shown(self):
        """Confirmed annotations don't add extra text to the prompt."""
        mem = make_memory("Finding")
        memories = RetrievedMemories(
            arena=[mem],
            annotations={str(mem.id): [
                {"annotation_type": "confirmed", "content": "Verified."}
            ]},
        )
        text = memories.format_for_prompt()
        # Confirmed is silently acknowledged
        assert "Verified" not in text

    def test_no_annotations_clean_output(self):
        mem = make_memory("Finding", key_conclusions=["A is true"])
        memories = RetrievedMemories(arena=[mem])
        text = memories.format_for_prompt()
        assert "WARNING" not in text
        assert "correction" not in text
