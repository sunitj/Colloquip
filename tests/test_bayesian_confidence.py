"""Tests for Bayesian confidence, temporal decay, composite scoring, and retrieval logging."""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from colloquip.embeddings.mock import MockEmbeddingProvider
from colloquip.memory.retriever import MemoryRetriever, RetrievedMemories
from colloquip.memory.store import (
    ANNOTATION_UPDATES,
    CONFIDENCE_CEILING,
    CONFIDENCE_FLOOR,
    DEFAULT_DECAY_HALF_LIFE_DAYS,
    DEFAULT_PRIOR,
    INITIAL_PRIORS,
    OUTCOME_UPDATES,
    InMemoryStore,
    SynthesisMemory,
    composite_score,
    compute_confidence,
    temporal_decay,
)

SUB_A = uuid4()
SUB_B = uuid4()


def make_memory(
    topic: str,
    subreddit_id=None,
    subreddit_name: str = "target_validation",
    key_conclusions: list | None = None,
    embedding: list | None = None,
    confidence_level: str = "high",
    confidence_alpha: float = 2.0,
    confidence_beta: float = 1.0,
    created_at: datetime | None = None,
) -> SynthesisMemory:
    return SynthesisMemory(
        thread_id=uuid4(),
        subreddit_id=subreddit_id or SUB_A,
        subreddit_name=subreddit_name,
        topic=topic,
        synthesis_content=f"Synthesis about {topic}",
        key_conclusions=key_conclusions or [f"Conclusion about {topic}"],
        citations_used=["PUBMED:12345678"],
        agents_involved=["biology", "chemistry"],
        template_type="assessment",
        confidence_level=confidence_level,
        confidence_alpha=confidence_alpha,
        confidence_beta=confidence_beta,
        embedding=embedding or [],
        created_at=created_at or datetime.now(timezone.utc),
    )


# --- compute_confidence ---


class TestComputeConfidence:
    def test_default_prior(self):
        # alpha=2, beta=1 -> 2/3 ≈ 0.667
        conf = compute_confidence(2.0, 1.0)
        assert abs(conf - 2 / 3) < 0.001

    def test_high_confidence(self):
        conf = compute_confidence(10.0, 1.0)
        assert conf <= CONFIDENCE_CEILING

    def test_low_confidence(self):
        conf = compute_confidence(1.0, 10.0)
        assert conf >= CONFIDENCE_FLOOR

    def test_zero_total(self):
        assert compute_confidence(0.0, 0.0) == 0.5

    def test_floor_enforced(self):
        # Very low alpha relative to beta
        conf = compute_confidence(0.01, 100.0)
        assert conf >= CONFIDENCE_FLOOR

    def test_ceiling_enforced(self):
        # Very high alpha relative to beta
        conf = compute_confidence(100.0, 0.01)
        assert conf <= CONFIDENCE_CEILING


# --- temporal_decay ---


class TestTemporalDecay:
    def test_brand_new_memory(self):
        now = datetime.now(timezone.utc)
        assert temporal_decay(now, now=now) == pytest.approx(1.0)

    def test_one_half_life_old(self):
        now = datetime.now(timezone.utc)
        created = now - timedelta(days=DEFAULT_DECAY_HALF_LIFE_DAYS)
        decay = temporal_decay(created, now=now)
        assert decay == pytest.approx(0.5, abs=0.01)

    def test_two_half_lives_old(self):
        now = datetime.now(timezone.utc)
        created = now - timedelta(days=2 * DEFAULT_DECAY_HALF_LIFE_DAYS)
        decay = temporal_decay(created, now=now)
        assert decay == pytest.approx(0.25, abs=0.01)

    def test_custom_half_life(self):
        now = datetime.now(timezone.utc)
        created = now - timedelta(days=30)
        decay = temporal_decay(created, now=now, half_life_days=30.0)
        assert decay == pytest.approx(0.5, abs=0.01)

    def test_zero_half_life_returns_one(self):
        now = datetime.now(timezone.utc)
        created = now - timedelta(days=365)
        assert temporal_decay(created, now=now, half_life_days=0.0) == 1.0

    def test_future_memory_returns_one(self):
        now = datetime.now(timezone.utc)
        future = now + timedelta(days=10)
        assert temporal_decay(future, now=now) == pytest.approx(1.0)


# --- composite_score ---


class TestCompositeScore:
    def test_new_high_confidence_high_similarity(self):
        now = datetime.now(timezone.utc)
        score = composite_score(
            similarity=0.9,
            alpha=10.0,
            beta=1.0,
            created_at=now,
            now=now,
        )
        # sim * conf * decay ≈ 0.9 * 0.909 * 1.0 ≈ 0.818
        assert score > 0.7

    def test_old_low_confidence_penalized(self):
        now = datetime.now(timezone.utc)
        old = now - timedelta(days=240)  # 2 half-lives
        score = composite_score(
            similarity=0.9,
            alpha=1.0,
            beta=5.0,
            created_at=old,
            now=now,
        )
        # sim * conf * decay ≈ 0.9 * 0.167 * 0.25 ≈ 0.037
        assert score < 0.1

    def test_same_similarity_newer_wins(self):
        now = datetime.now(timezone.utc)
        new = now - timedelta(days=1)
        old = now - timedelta(days=200)
        score_new = composite_score(0.8, 2.0, 1.0, new, now=now)
        score_old = composite_score(0.8, 2.0, 1.0, old, now=now)
        assert score_new > score_old

    def test_same_age_higher_confidence_wins(self):
        now = datetime.now(timezone.utc)
        created = now - timedelta(days=30)
        score_high = composite_score(0.8, 10.0, 1.0, created, now=now)
        score_low = composite_score(0.8, 1.0, 5.0, created, now=now)
        assert score_high > score_low


# --- SynthesisMemory.confidence property ---


class TestSynthesisMemoryConfidence:
    def test_default_confidence(self):
        mem = make_memory("test")
        assert abs(mem.confidence - 2 / 3) < 0.001

    def test_high_prior(self):
        mem = make_memory("test", confidence_alpha=3.0, confidence_beta=1.0)
        assert mem.confidence == pytest.approx(0.75, abs=0.01)

    def test_low_prior(self):
        mem = make_memory("test", confidence_alpha=1.0, confidence_beta=2.0)
        assert mem.confidence == pytest.approx(1 / 3, abs=0.01)


# --- INITIAL_PRIORS ---


class TestInitialPriors:
    def test_high_prior(self):
        alpha, beta = INITIAL_PRIORS["high"]
        conf = compute_confidence(alpha, beta)
        assert conf > 0.7

    def test_moderate_prior(self):
        alpha, beta = INITIAL_PRIORS["moderate"]
        conf = compute_confidence(alpha, beta)
        assert 0.4 < conf < 0.7

    def test_low_prior(self):
        alpha, beta = INITIAL_PRIORS["low"]
        conf = compute_confidence(alpha, beta)
        assert conf < 0.4

    def test_default_prior_is_optimistic(self):
        alpha, beta = DEFAULT_PRIOR
        conf = compute_confidence(alpha, beta)
        assert conf > 0.5


# --- InMemoryStore: Bayesian updates ---


class TestBayesianUpdates:
    @pytest.fixture
    def store(self):
        return InMemoryStore()

    @pytest.mark.asyncio
    async def test_update_confidence_increases_alpha(self, store):
        mem = make_memory("test", confidence_alpha=2.0, confidence_beta=1.0)
        await store.save(mem)

        updated = await store.update_confidence(mem.id, delta_alpha=1.0)
        assert updated is not None
        assert updated.confidence_alpha == 3.0
        assert updated.confidence_beta == 1.0

    @pytest.mark.asyncio
    async def test_update_confidence_increases_beta(self, store):
        mem = make_memory("test", confidence_alpha=2.0, confidence_beta=1.0)
        original_confidence = mem.confidence  # capture before mutation
        await store.save(mem)

        updated = await store.update_confidence(mem.id, delta_beta=2.0)
        assert updated.confidence_beta == 3.0
        assert updated.confidence < original_confidence  # Confidence decreased

    @pytest.mark.asyncio
    async def test_update_nonexistent_returns_none(self, store):
        result = await store.update_confidence(uuid4(), delta_alpha=1.0)
        assert result is None

    @pytest.mark.asyncio
    async def test_update_persists(self, store):
        mem = make_memory("test", confidence_alpha=2.0, confidence_beta=1.0)
        await store.save(mem)
        await store.update_confidence(mem.id, delta_alpha=5.0)

        retrieved = await store.get(mem.id)
        assert retrieved.confidence_alpha == 7.0

    @pytest.mark.asyncio
    async def test_alpha_beta_dont_go_negative(self, store):
        mem = make_memory("test", confidence_alpha=1.0, confidence_beta=1.0)
        await store.save(mem)
        updated = await store.update_confidence(mem.id, delta_alpha=-5.0, delta_beta=-5.0)
        assert updated.confidence_alpha == 0.0
        assert updated.confidence_beta == 0.0


# --- InMemoryStore: annotation triggers confidence update ---


class TestAnnotationConfidenceUpdates:
    @pytest.fixture
    def store(self):
        return InMemoryStore()

    @pytest.mark.asyncio
    async def test_confirmed_annotation_increases_alpha(self, store):
        mem = make_memory("test", confidence_alpha=2.0, confidence_beta=1.0)
        await store.save(mem)

        await store.annotate(mem.id, "confirmed", "Verified by experiment.")
        updated = await store.get(mem.id)
        da, db = ANNOTATION_UPDATES["confirmed"]
        assert updated.confidence_alpha == 2.0 + da
        assert updated.confidence_beta == 1.0 + db

    @pytest.mark.asyncio
    async def test_correction_annotation_increases_beta(self, store):
        mem = make_memory("test", confidence_alpha=2.0, confidence_beta=1.0)
        await store.save(mem)

        await store.annotate(mem.id, "correction", "Conclusion was wrong.")
        updated = await store.get(mem.id)
        da, db = ANNOTATION_UPDATES["correction"]
        assert updated.confidence_alpha == 2.0 + da
        assert updated.confidence_beta == 1.0 + db

    @pytest.mark.asyncio
    async def test_outdated_annotation_increases_beta(self, store):
        mem = make_memory("test", confidence_alpha=2.0, confidence_beta=1.0)
        await store.save(mem)

        await store.annotate(mem.id, "outdated", "Superseded by new data.")
        updated = await store.get(mem.id)
        da, db = ANNOTATION_UPDATES["outdated"]
        assert updated.confidence_beta == 1.0 + db

    @pytest.mark.asyncio
    async def test_context_annotation_no_change(self, store):
        mem = make_memory("test", confidence_alpha=2.0, confidence_beta=1.0)
        await store.save(mem)

        await store.annotate(mem.id, "context", "Additional background info.")
        updated = await store.get(mem.id)
        assert updated.confidence_alpha == 2.0
        assert updated.confidence_beta == 1.0

    @pytest.mark.asyncio
    async def test_multiple_annotations_compound(self, store):
        mem = make_memory("test", confidence_alpha=2.0, confidence_beta=1.0)
        await store.save(mem)

        await store.annotate(mem.id, "confirmed", "First verification.")
        await store.annotate(mem.id, "confirmed", "Second verification.")

        updated = await store.get(mem.id)
        da, _ = ANNOTATION_UPDATES["confirmed"]
        assert updated.confidence_alpha == pytest.approx(2.0 + 2 * da)


# --- Composite scoring in search ---


class TestCompositeSearchScoring:
    @pytest.fixture
    def store(self):
        return InMemoryStore()

    @pytest.fixture
    def provider(self):
        return MockEmbeddingProvider(dimension=64)

    @pytest.mark.asyncio
    async def test_high_confidence_ranks_above_low(self, store, provider):
        emb = await provider.embed("kinase inhibitor")
        high = make_memory(
            "kinase high",
            subreddit_id=SUB_A,
            embedding=emb,
            confidence_alpha=10.0,
            confidence_beta=1.0,
        )
        low = make_memory(
            "kinase low",
            subreddit_id=SUB_A,
            embedding=emb,
            confidence_alpha=1.0,
            confidence_beta=10.0,
        )
        await store.save(high)
        await store.save(low)

        query = await provider.embed("kinase inhibitor")
        results = await store.search(query, subreddit_id=SUB_A, limit=2)

        assert len(results) == 2
        assert results[0].memory.topic == "kinase high"
        assert results[0].score > results[1].score

    @pytest.mark.asyncio
    async def test_newer_memory_ranks_above_older(self, store, provider):
        emb = await provider.embed("GLP-1 receptor")
        now = datetime.now(timezone.utc)
        new = make_memory(
            "GLP-1 new",
            subreddit_id=SUB_A,
            embedding=emb,
            created_at=now - timedelta(days=1),
        )
        old = make_memory(
            "GLP-1 old",
            subreddit_id=SUB_A,
            embedding=emb,
            created_at=now - timedelta(days=300),
        )
        await store.save(new)
        await store.save(old)

        query = await provider.embed("GLP-1 receptor")
        results = await store.search(query, subreddit_id=SUB_A, limit=2)

        assert results[0].memory.topic == "GLP-1 new"
        assert results[0].score > results[1].score

    @pytest.mark.asyncio
    async def test_search_results_have_score_field(self, store, provider):
        emb = await provider.embed("test topic")
        mem = make_memory("test", subreddit_id=SUB_A, embedding=emb)
        await store.save(mem)

        query = await provider.embed("test topic")
        results = await store.search(query, subreddit_id=SUB_A, limit=1)
        assert len(results) == 1
        assert results[0].score > 0
        assert results[0].similarity > 0

    @pytest.mark.asyncio
    async def test_global_search_uses_composite(self, store, provider):
        emb = await provider.embed("biology topic")
        high = make_memory(
            "bio high",
            subreddit_id=SUB_B,
            embedding=emb,
            confidence_alpha=10.0,
            confidence_beta=1.0,
        )
        low = make_memory(
            "bio low",
            subreddit_id=SUB_B,
            embedding=emb,
            confidence_alpha=1.0,
            confidence_beta=10.0,
        )
        await store.save(high)
        await store.save(low)

        query = await provider.embed("biology topic")
        results = await store.search_global(query, exclude_subreddit=SUB_A, limit=2)

        assert results[0].memory.topic == "bio high"


# --- Retrieval logging ---


class TestRetrievalLogging:
    @pytest.fixture
    def store(self):
        return InMemoryStore()

    @pytest.fixture
    def provider(self):
        return MockEmbeddingProvider(dimension=64)

    @pytest.fixture
    def retriever(self, store, provider):
        return MemoryRetriever(store=store, embedding_provider=provider)

    @pytest.mark.asyncio
    async def test_retrieval_creates_log_entries(self, retriever, store, provider):
        emb = await provider.embed("drug target")
        mem = make_memory("drug target analysis", subreddit_id=SUB_A, embedding=emb)
        await store.save(mem)

        await retriever.retrieve("drug target", subreddit_id=SUB_A)

        log = store.get_retrieval_log()
        assert len(log) >= 1
        entry = log[0]
        assert entry.memory_id == mem.id
        assert entry.query_topic == "drug target"
        assert entry.scope == "arena"
        assert entry.similarity > 0
        assert entry.confidence > 0
        assert entry.decay_factor > 0
        assert entry.composite_score > 0

    @pytest.mark.asyncio
    async def test_retrieval_logs_both_scopes(self, retriever, store, provider):
        emb_a = await provider.embed("shared topic data")
        emb_b = await provider.embed("shared topic analysis")
        await store.save(make_memory("arena", subreddit_id=SUB_A, embedding=emb_a))
        await store.save(make_memory("global", subreddit_id=SUB_B, embedding=emb_b))

        await retriever.retrieve("shared topic", subreddit_id=SUB_A)

        log = store.get_retrieval_log()
        scopes = {e.scope for e in log}
        assert "arena" in scopes
        assert "global" in scopes

    @pytest.mark.asyncio
    async def test_empty_retrieval_no_log(self, retriever, store):
        await retriever.retrieve("nothing", subreddit_id=SUB_A)
        assert store.get_retrieval_log() == []

    @pytest.mark.asyncio
    async def test_retrieval_scores_in_result(self, retriever, store, provider):
        emb = await provider.embed("test topic data")
        mem = make_memory("test topic", subreddit_id=SUB_A, embedding=emb)
        await store.save(mem)

        result = await retriever.retrieve("test topic", subreddit_id=SUB_A)
        assert str(mem.id) in result.scores
        assert result.scores[str(mem.id)] > 0


# --- Prompt formatting with numeric confidence ---


class TestConfidenceInFormatting:
    def test_format_shows_percentage(self):
        mem = make_memory(
            "GLP-1 agonists",
            key_conclusions=["Effective in diabetes"],
            confidence_alpha=3.0,
            confidence_beta=1.0,
        )
        memories = RetrievedMemories(arena=[mem])
        text = memories.format_for_prompt()

        assert "Confidence: 75%" in text
        assert "GLP-1 agonists" in text

    def test_format_low_confidence(self):
        mem = make_memory(
            "Uncertain finding",
            key_conclusions=["Preliminary result"],
            confidence_alpha=1.0,
            confidence_beta=5.0,
        )
        memories = RetrievedMemories(arena=[mem])
        text = memories.format_for_prompt()

        assert "Confidence: 17%" in text

    def test_format_global_also_shows_confidence(self):
        mem = make_memory(
            "Cross-sub finding",
            subreddit_name="oncology",
            key_conclusions=["Shared conclusion"],
            confidence_alpha=5.0,
            confidence_beta=1.0,
        )
        memories = RetrievedMemories(global_results=[mem])
        text = memories.format_for_prompt()

        assert "Confidence: 83%" in text
        assert "[oncology]" in text


# --- OUTCOME_UPDATES constants ---


class TestOutcomeUpdates:
    def test_confirmed_boosts_alpha(self):
        da, db = OUTCOME_UPDATES["confirmed"]
        assert da > 0
        assert db == 0

    def test_contradicted_asymmetric(self):
        da, db = OUTCOME_UPDATES["contradicted"]
        assert da == 0
        assert db > 0
        # Contradictions hurt more than confirmations help
        confirm_da, _ = OUTCOME_UPDATES["confirmed"]
        assert db > confirm_da

    def test_inconclusive_no_change(self):
        da, db = OUTCOME_UPDATES["inconclusive"]
        assert da == 0
        assert db == 0
