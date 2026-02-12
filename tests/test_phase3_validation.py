"""Phase 3 end-to-end validation tests.

Validates the full memory pipeline:
1. Syntheses are stored as memories with embeddings
2. Retrieval finds related memories by topic similarity
3. Retrieved memories are formatted into agent prompts
4. Annotations propagate through to prompts
5. Phase 3b models are defined and valid
"""

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from colloquip.agents.prompts import build_memory_context, build_v3_system_prompt
from colloquip.embeddings.mock import MockEmbeddingProvider
from colloquip.memory.extractor import SynthesisMemoryExtractor
from colloquip.memory.retriever import MemoryRetriever
from colloquip.memory.store import InMemoryStore, SynthesisMemory
from colloquip.models import (
    AuditChain,
    MemoryAnnotationType,
    MemoryScope,
    MemoryType,
    Phase,
    Synthesis,
    TypedMemory,
)


SUB_VALIDATION = uuid4()
SUB_ONCOLOGY = uuid4()


@pytest.fixture
def provider():
    return MockEmbeddingProvider(dimension=64)


@pytest.fixture
def store():
    return InMemoryStore()


@pytest.fixture
def extractor(provider):
    return SynthesisMemoryExtractor(embedding_provider=provider)


@pytest.fixture
def retriever(store, provider):
    return MemoryRetriever(store=store, embedding_provider=provider)


class TestPhase3EndToEnd:
    """End-to-end validation of the Phase 3 memory pipeline."""

    @pytest.mark.asyncio
    async def test_synthesis_to_memory_to_retrieval(self, store, extractor, retriever):
        """Run multiple syntheses, store them, then retrieve for a new topic."""
        topics = [
            "GLP-1 receptor agonists improve cognitive function",
            "GLP-1 agonist semaglutide reduces neuroinflammation",
            "Incretin hormones and neuroprotection mechanisms",
            "SGLT2 inhibitors improve kidney function",
            "Quantum computing applications in drug discovery",
        ]

        for topic in topics:
            synthesis = Synthesis(
                thread_id=uuid4(),
                template_type="assessment",
                sections={
                    "executive_summary": f"Analysis of {topic}.",
                    "key_findings": f"- {topic} shows promising evidence\n- More research needed",
                },
                metadata={"confidence_level": "moderate"},
                audit_chains=[AuditChain(claim=topic, dissenting_agents=["red_team"])],
            )

            memory = await extractor.extract(
                synthesis=synthesis,
                topic=topic,
                subreddit_id=SUB_VALIDATION,
                subreddit_name="target_validation",
            )
            await store.save(memory)

        assert await store.count() == 5

        # 5th deliberation on GLP-1 topic should find related memories
        result = await retriever.retrieve(
            "GLP-1 cognitive benefits and neuroprotection",
            subreddit_id=SUB_VALIDATION,
            max_arena=3,
        )

        # Should find GLP-1 related memories, not SGLT2 or quantum
        assert len(result.arena) == 3
        topics_found = [m.topic for m in result.arena]
        assert any("GLP-1" in t for t in topics_found)
        # Quantum computing should not be in top-3
        assert not any("Quantum" in t for t in topics_found)

    @pytest.mark.asyncio
    async def test_annotations_propagate_to_prompt(self, store, extractor, retriever):
        """Annotations added to memories appear in agent prompts."""
        synthesis = Synthesis(
            thread_id=uuid4(),
            template_type="assessment",
            sections={
                "executive_summary": "Analysis of target validation.",
                "key_findings": "- IC50 of 5nM confirmed by internal assay",
            },
            metadata={"confidence_level": "high"},
        )

        memory = await extractor.extract(
            synthesis=synthesis,
            topic="BRCA1 target validation",
            subreddit_id=SUB_VALIDATION,
            subreddit_name="target_validation",
        )
        await store.save(memory)

        # Human marks the IC50 as outdated
        await store.annotate(
            memory.id, "outdated", "IC50 was revised to 50nM in latest assay."
        )

        # Retrieve and format
        result = await retriever.retrieve(
            "BRCA1 target validation progress",
            subreddit_id=SUB_VALIDATION,
        )

        assert len(result.arena) == 1
        assert str(memory.id) in result.annotations

        # Format for prompt
        memory_text = result.format_for_prompt()
        assert "WARNING - OUTDATED" in memory_text
        assert "IC50 was revised to 50nM" in memory_text

        # Build full agent prompt
        prompt = build_v3_system_prompt(
            persona_prompt="You are a biology expert.",
            phase=Phase.EXPLORE,
            prior_deliberations=memory_text,
        )
        assert "IC50 was revised to 50nM" in prompt
        assert "REFERENCE prior conclusions" in prompt

    @pytest.mark.asyncio
    async def test_cross_subreddit_retrieval(self, store, extractor, retriever):
        """Memories from other subreddits appear in global results."""
        for sub_id, sub_name, topic in [
            (SUB_VALIDATION, "target_validation", "CDK4 inhibitor target validation"),
            (SUB_ONCOLOGY, "oncology", "CDK4/6 inhibitors in breast cancer treatment"),
        ]:
            synthesis = Synthesis(
                thread_id=uuid4(),
                template_type="assessment",
                sections={"executive_summary": f"Analysis of {topic}"},
                metadata={},
            )
            memory = await extractor.extract(
                synthesis=synthesis,
                topic=topic,
                subreddit_id=sub_id,
                subreddit_name=sub_name,
            )
            await store.save(memory)

        # Search from target_validation: should find oncology as global
        result = await retriever.retrieve(
            "CDK4 inhibitor analysis",
            subreddit_id=SUB_VALIDATION,
        )
        assert len(result.arena) == 1
        assert result.arena[0].subreddit_name == "target_validation"
        assert len(result.global_results) == 1
        assert result.global_results[0].subreddit_name == "oncology"


class TestPhase3bModels:
    """Phase 3b typed memory models are correctly defined."""

    def test_memory_type_enum(self):
        assert len(MemoryType) == 5
        assert MemoryType.FACTUAL == "factual"
        assert MemoryType.METHODOLOGICAL == "methodological"
        assert MemoryType.POSITIONAL == "positional"
        assert MemoryType.RELATIONAL == "relational"
        assert MemoryType.CONTEXTUAL == "contextual"

    def test_memory_scope_enum(self):
        assert MemoryScope.GLOBAL == "global"
        assert MemoryScope.ARENA == "arena"

    def test_typed_memory_creation(self):
        tm = TypedMemory(
            source_memory_id=uuid4(),
            memory_type=MemoryType.FACTUAL,
            scope=MemoryScope.GLOBAL,
            content="GLP-1 receptor agonists bind GLP-1R with Ki of 0.5nM",
            confidence=0.85,
            entities=["GLP-1", "GLP-1R"],
            subreddit_id=uuid4(),
        )
        assert tm.memory_type == MemoryType.FACTUAL
        assert tm.scope == MemoryScope.GLOBAL
        assert tm.confidence == 0.85
        assert len(tm.entities) == 2

    def test_typed_memory_confidence_bounds(self):
        with pytest.raises(Exception):
            TypedMemory(
                source_memory_id=uuid4(),
                memory_type=MemoryType.FACTUAL,
                scope=MemoryScope.GLOBAL,
                content="test",
                confidence=1.5,  # Out of bounds
                subreddit_id=uuid4(),
            )
