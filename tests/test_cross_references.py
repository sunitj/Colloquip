"""Tests for cross-subreddit reference detection."""

from uuid import uuid4

import pytest

from colloquip.embeddings.mock import MockEmbeddingProvider
from colloquip.memory.cross_references import (
    CrossReference,
    CrossReferenceDetector,
    extract_entities,
)
from colloquip.memory.store import InMemoryStore, SynthesisMemory

SUB_A = uuid4()
SUB_B = uuid4()


def make_memory(
    topic: str,
    subreddit_id=None,
    subreddit_name="sub_a",
    key_conclusions=None,
    synthesis_content="",
    embedding=None,
    **kwargs,
) -> SynthesisMemory:
    return SynthesisMemory(
        thread_id=uuid4(),
        subreddit_id=subreddit_id or SUB_A,
        subreddit_name=subreddit_name,
        topic=topic,
        synthesis_content=synthesis_content,
        key_conclusions=(
            key_conclusions if key_conclusions is not None else [f"Conclusion about {topic}"]
        ),
        embedding=embedding or [],
        **kwargs,
    )


# --- Entity extraction ---


class TestEntityExtraction:
    def test_extract_pmids(self):
        text = "See PMID:12345 and PMID:67890 for details."
        entities = extract_entities(text)
        assert "PMID:12345" in entities
        assert "PMID:67890" in entities

    def test_extract_pmid_with_space(self):
        text = "Reference PMID 99999."
        entities = extract_entities(text)
        assert "PMID:99999" in entities

    def test_extract_gene_names(self):
        text = "The GLP1R gene and BRCA1 are important."
        entities = extract_entities(text)
        assert any("GENE:" in e for e in entities)

    def test_extract_compound_ids(self):
        text = "Compound GLP-123 showed efficacy."
        entities = extract_entities(text)
        assert "COMPOUND:GLP-123" in entities

    def test_no_entities_in_plain_text(self):
        text = "a simple sentence with no entities"
        entities = extract_entities(text)
        # Should only find things matching patterns; common words filtered
        assert not any(e.startswith("PMID:") for e in entities)

    def test_common_words_filtered(self):
        text = "THE AND FOR ARE"
        entities = extract_entities(text)
        assert "GENE:THE" not in entities
        assert "GENE:AND" not in entities


# --- CrossReference model ---


class TestCrossReferenceModel:
    def test_create_cross_reference(self):
        ref = CrossReference(
            source_memory_id=uuid4(),
            target_memory_id=uuid4(),
            source_subreddit_id=SUB_A,
            target_subreddit_id=SUB_B,
            source_subreddit_name="sub_a",
            target_subreddit_name="sub_b",
            similarity=0.85,
            shared_entities=["PMID:12345"],
            reasoning="Test reasoning",
        )
        assert ref.status == "pending"
        assert ref.similarity == 0.85


# --- CrossReferenceDetector ---


class TestCrossReferenceDetector:
    @pytest.fixture
    def provider(self):
        return MockEmbeddingProvider(dimension=64)

    @pytest.fixture
    def store(self):
        return InMemoryStore()

    @pytest.fixture
    def detector(self, store, provider):
        return CrossReferenceDetector(
            memory_store=store,
            embedding_provider=provider,
            similarity_threshold=0.5,  # Lower threshold for testing
        )

    @pytest.mark.asyncio
    async def test_detect_cross_reference(self, detector, store, provider):
        """Two memories in different subreddits with shared entities should be detected."""
        emb = await provider.embed("GLP-1 BRCA1 PMID:12345 drug target")
        mem_a = make_memory(
            topic="GLP-1 BRCA1 drug target assessment",
            subreddit_id=SUB_A,
            subreddit_name="target_validation",
            key_conclusions=["GLP-1 BRCA1 is viable target PMID:12345"],
            synthesis_content="Study PMID:12345 shows GLP-1 BRCA1 efficacy.",
            embedding=emb,
        )
        mem_b = make_memory(
            topic="GLP-1 BRCA1 drug target analysis",
            subreddit_id=SUB_B,
            subreddit_name="chemistry",
            key_conclusions=["GLP-1 BRCA1 compound synthesis feasible PMID:12345"],
            synthesis_content="PMID:12345 relevant to GLP-1 BRCA1 compounds.",
            embedding=emb,
        )
        await store.save(mem_a)
        await store.save(mem_b)

        refs = await detector.detect_for_memory(mem_a)
        assert len(refs) == 1
        assert refs[0].target_memory_id == mem_b.id
        assert len(refs[0].shared_entities) > 0

    @pytest.mark.asyncio
    async def test_no_cross_ref_same_subreddit(self, detector, store, provider):
        """Memories in the same subreddit should not be detected."""
        emb = await provider.embed("GLP-1 PMID:12345")
        mem_a = make_memory(
            topic="Topic A PMID:12345",
            subreddit_id=SUB_A,
            synthesis_content="PMID:12345",
            embedding=emb,
        )
        mem_b = make_memory(
            topic="Topic B PMID:12345",
            subreddit_id=SUB_A,
            synthesis_content="PMID:12345",
            embedding=emb,
        )
        await store.save(mem_a)
        await store.save(mem_b)

        refs = await detector.detect_for_memory(mem_a)
        assert len(refs) == 0  # Same subreddit excluded

    @pytest.mark.asyncio
    async def test_no_cross_ref_no_shared_entities(self, detector, store, provider):
        """Memories without shared entities should not be detected."""
        emb = await provider.embed("completely different topics")
        mem_a = make_memory(
            topic="Topic about gardening",
            subreddit_id=SUB_A,
            synthesis_content="How to grow plants.",
            embedding=emb,
        )
        mem_b = make_memory(
            topic="Topic about cooking",
            subreddit_id=SUB_B,
            subreddit_name="sub_b",
            synthesis_content="How to make food.",
            embedding=emb,
        )
        await store.save(mem_a)
        await store.save(mem_b)

        refs = await detector.detect_for_memory(mem_a)
        assert len(refs) == 0

    @pytest.mark.asyncio
    async def test_no_cross_ref_without_conclusions(self, detector, store, provider):
        """Memories without key conclusions fail the actionability check."""
        emb = await provider.embed("GLP-1 PMID:12345")
        mem_a = make_memory(
            topic="Topic PMID:12345",
            subreddit_id=SUB_A,
            key_conclusions=["Has conclusions PMID:12345"],
            synthesis_content="PMID:12345",
            embedding=emb,
        )
        mem_b = make_memory(
            topic="Topic PMID:12345",
            subreddit_id=SUB_B,
            subreddit_name="sub_b",
            key_conclusions=[],
            synthesis_content="PMID:12345",
            embedding=emb,
        )
        await store.save(mem_a)
        await store.save(mem_b)

        refs = await detector.detect_for_memory(mem_a)
        assert len(refs) == 0

    @pytest.mark.asyncio
    async def test_no_embedding_skips(self, detector, store):
        """Memories without embeddings should be skipped."""
        mem = make_memory(topic="No embedding", embedding=[])
        refs = await detector.detect_for_memory(mem)
        assert refs == []
