"""Tests for memory store and retriever."""

from uuid import uuid4

import pytest

from colloquip.embeddings.mock import MockEmbeddingProvider
from colloquip.memory.retriever import MemoryRetriever, RetrievedMemories
from colloquip.memory.store import InMemoryStore, SynthesisMemory

# --- Fixtures ---

SUB_A = uuid4()
SUB_B = uuid4()
SUB_C = uuid4()


def make_memory(
    topic: str,
    subreddit_id=SUB_A,
    subreddit_name: str = "target_validation",
    key_conclusions: list | None = None,
    embedding: list | None = None,
    confidence_level: str = "high",
    template_type: str = "assessment",
) -> SynthesisMemory:
    return SynthesisMemory(
        thread_id=uuid4(),
        subreddit_id=subreddit_id,
        subreddit_name=subreddit_name,
        topic=topic,
        synthesis_content=f"Synthesis about {topic}",
        key_conclusions=key_conclusions or [f"Conclusion about {topic}"],
        citations_used=["PUBMED:12345678"],
        agents_involved=["biology", "chemistry"],
        template_type=template_type,
        confidence_level=confidence_level,
        embedding=embedding or [],
    )


@pytest.fixture
def store():
    return InMemoryStore()


@pytest.fixture
def provider():
    return MockEmbeddingProvider(dimension=64)


@pytest.fixture
def retriever(store, provider):
    return MemoryRetriever(store=store, embedding_provider=provider)


# --- InMemoryStore ---


class TestInMemoryStore:
    @pytest.mark.asyncio
    async def test_save_and_get(self, store):
        mem = make_memory("BRCA1 target validation")
        await store.save(mem)

        retrieved = await store.get(mem.id)
        assert retrieved is not None
        assert retrieved.topic == "BRCA1 target validation"

    @pytest.mark.asyncio
    async def test_get_nonexistent_returns_none(self, store):
        result = await store.get(uuid4())
        assert result is None

    @pytest.mark.asyncio
    async def test_count(self, store):
        assert await store.count() == 0
        await store.save(make_memory("topic 1"))
        assert await store.count() == 1
        await store.save(make_memory("topic 2"))
        assert await store.count() == 2

    @pytest.mark.asyncio
    async def test_save_update_existing(self, store):
        mem = make_memory("original topic")
        await store.save(mem)

        mem.topic = "updated topic"
        await store.save(mem)

        assert await store.count() == 1
        retrieved = await store.get(mem.id)
        assert retrieved.topic == "updated topic"

    @pytest.mark.asyncio
    async def test_list_by_subreddit(self, store):
        await store.save(make_memory("topic A", subreddit_id=SUB_A))
        await store.save(make_memory("topic B", subreddit_id=SUB_A))
        await store.save(make_memory("topic C", subreddit_id=SUB_B))

        results = await store.list_by_subreddit(SUB_A)
        assert len(results) == 2
        assert all(m.subreddit_id == SUB_A for m in results)

    @pytest.mark.asyncio
    async def test_list_by_subreddit_empty(self, store):
        results = await store.list_by_subreddit(uuid4())
        assert results == []

    @pytest.mark.asyncio
    async def test_search_by_subreddit_scope(self, store, provider):
        emb_a = await provider.embed("kinase inhibitor drug target")
        emb_b = await provider.embed("protein folding structure")
        emb_c = await provider.embed("kinase inhibitor drug candidate")

        await store.save(make_memory("kinase A", subreddit_id=SUB_A, embedding=emb_a))
        await store.save(make_memory("protein B", subreddit_id=SUB_A, embedding=emb_b))
        await store.save(make_memory("kinase C", subreddit_id=SUB_B, embedding=emb_c))

        query = await provider.embed("kinase inhibitor")
        results = await store.search(query, subreddit_id=SUB_A, limit=2)

        assert len(results) <= 2
        assert all(r.memory.subreddit_id == SUB_A for r in results)

    @pytest.mark.asyncio
    async def test_search_ranked_by_similarity(self, store, provider):
        emb_close = await provider.embed("GLP-1 receptor agonist diabetes")
        emb_far = await provider.embed("quantum computing neural networks")

        await store.save(make_memory("GLP-1", subreddit_id=SUB_A, embedding=emb_close))
        await store.save(make_memory("quantum", subreddit_id=SUB_A, embedding=emb_far))

        query = await provider.embed("GLP-1 receptor agonist")
        results = await store.search(query, subreddit_id=SUB_A, limit=2)

        assert len(results) == 2
        assert results[0].similarity > results[1].similarity
        assert results[0].memory.topic == "GLP-1"

    @pytest.mark.asyncio
    async def test_search_respects_limit(self, store, provider):
        for i in range(5):
            emb = await provider.embed(f"topic number {i}")
            await store.save(make_memory(f"topic {i}", subreddit_id=SUB_A, embedding=emb))

        query = await provider.embed("topic")
        results = await store.search(query, subreddit_id=SUB_A, limit=2)
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_search_skips_no_embedding(self, store, provider):
        await store.save(make_memory("no embedding", subreddit_id=SUB_A, embedding=[]))
        emb = await provider.embed("has embedding")
        await store.save(make_memory("has embedding", subreddit_id=SUB_A, embedding=emb))

        query = await provider.embed("test")
        results = await store.search(query, subreddit_id=SUB_A, limit=5)
        assert len(results) == 1
        assert results[0].memory.topic == "has embedding"

    @pytest.mark.asyncio
    async def test_search_global_excludes_subreddit(self, store, provider):
        emb_a = await provider.embed("target validation biology")
        emb_b = await provider.embed("target validation chemistry")
        emb_c = await provider.embed("target validation analysis")

        await store.save(make_memory("A", subreddit_id=SUB_A, embedding=emb_a))
        await store.save(make_memory("B", subreddit_id=SUB_B, embedding=emb_b))
        await store.save(make_memory("C", subreddit_id=SUB_C, embedding=emb_c))

        query = await provider.embed("target validation")
        results = await store.search_global(query, exclude_subreddit=SUB_A, limit=5)

        assert len(results) == 2
        assert all(r.memory.subreddit_id != SUB_A for r in results)

    @pytest.mark.asyncio
    async def test_search_global_ranked_by_similarity(self, store, provider):
        emb_close = await provider.embed("kinase inhibitor target")
        emb_far = await provider.embed("unrelated topic entirely different")

        await store.save(make_memory("close", subreddit_id=SUB_B, embedding=emb_close))
        await store.save(make_memory("far", subreddit_id=SUB_C, embedding=emb_far))

        query = await provider.embed("kinase inhibitor")
        results = await store.search_global(query, exclude_subreddit=SUB_A, limit=2)

        assert results[0].memory.topic == "close"
        assert results[0].similarity > results[1].similarity


# --- MemoryRetriever ---


class TestMemoryRetriever:
    @pytest.mark.asyncio
    async def test_retrieve_arena_and_global(self, retriever, store, provider):
        emb_a = await provider.embed("drug target biology")
        emb_b = await provider.embed("drug target chemistry")

        await store.save(make_memory("arena mem", subreddit_id=SUB_A, embedding=emb_a))
        await store.save(
            make_memory(
                "global mem",
                subreddit_id=SUB_B,
                subreddit_name="chemistry",
                embedding=emb_b,
            )
        )

        result = await retriever.retrieve("drug target", subreddit_id=SUB_A)

        assert isinstance(result, RetrievedMemories)
        assert len(result.arena) == 1
        assert result.arena[0].topic == "arena mem"
        assert len(result.global_results) == 1
        assert result.global_results[0].topic == "global mem"

    @pytest.mark.asyncio
    async def test_retrieve_empty_store(self, retriever):
        result = await retriever.retrieve("anything", subreddit_id=SUB_A)
        assert result.arena == []
        assert result.global_results == []

    @pytest.mark.asyncio
    async def test_retrieve_respects_limits(self, retriever, store, provider):
        for i in range(5):
            emb = await provider.embed(f"topic {i} biology")
            await store.save(make_memory(f"topic {i}", subreddit_id=SUB_A, embedding=emb))

        result = await retriever.retrieve(
            "biology",
            subreddit_id=SUB_A,
            max_arena=2,
            max_global=1,
        )
        assert len(result.arena) <= 2

    @pytest.mark.asyncio
    async def test_retrieve_global_excludes_current(self, retriever, store, provider):
        emb = await provider.embed("shared topic")
        await store.save(make_memory("same sub", subreddit_id=SUB_A, embedding=emb))

        result = await retriever.retrieve("shared topic", subreddit_id=SUB_A)
        # The memory is in SUB_A, so it should not appear in global results
        assert all(m.subreddit_id != SUB_A for m in result.global_results)


# --- RetrievedMemories formatting ---


class TestRetrievedMemoriesFormatting:
    def test_format_empty(self):
        memories = RetrievedMemories()
        text = memories.format_for_prompt()
        assert "No relevant past deliberations found" in text

    def test_format_arena_only(self):
        mem = make_memory(
            "GLP-1 agonists",
            key_conclusions=["Effective in diabetes", "Cognitive benefits unclear"],
            confidence_level="moderate",
        )
        memories = RetrievedMemories(arena=[mem])
        text = memories.format_for_prompt()

        assert "This Subreddit" in text
        assert "GLP-1 agonists" in text
        assert "Effective in diabetes" in text
        assert "Cognitive benefits unclear" in text
        assert "Confidence:" in text
        assert "Other Subreddits" not in text

    def test_format_global_only(self):
        mem = make_memory(
            "BRCA2 analysis",
            subreddit_name="oncology",
            key_conclusions=["Strong genetic evidence"],
        )
        memories = RetrievedMemories(global_results=[mem])
        text = memories.format_for_prompt()

        assert "Other Subreddits" in text
        assert "[oncology]" in text
        assert "BRCA2 analysis" in text
        assert "Strong genetic evidence" in text

    def test_format_both_arena_and_global(self):
        arena = make_memory("arena topic", key_conclusions=["Arena conclusion"])
        global_mem = make_memory(
            "global topic",
            subreddit_name="chemistry",
            key_conclusions=["Global conclusion"],
        )
        memories = RetrievedMemories(arena=[arena], global_results=[global_mem])
        text = memories.format_for_prompt()

        assert "This Subreddit" in text
        assert "Other Subreddits" in text
        assert "Arena conclusion" in text
        assert "Global conclusion" in text

    def test_format_always_shows_numeric_confidence(self):
        mem = make_memory("topic", confidence_level="")
        memories = RetrievedMemories(arena=[mem])
        text = memories.format_for_prompt()
        # Numeric confidence is always shown regardless of confidence_level string
        assert "Confidence:" in text

    def test_format_multiple_arena_memories(self):
        mems = [make_memory(f"topic {i}", key_conclusions=[f"Conclusion {i}"]) for i in range(3)]
        memories = RetrievedMemories(arena=mems)
        text = memories.format_for_prompt()

        for i in range(3):
            assert f"topic {i}" in text
            assert f"Conclusion {i}" in text
