"""Tests for watcher infrastructure: interface, registry, and triage agent."""

from uuid import uuid4

import pytest

from colloquip.models import (
    TriageSignal,
    WatcherConfig,
    WatcherEvent,
    WatcherSource,
    WatcherType,
)
from colloquip.watchers.interface import BaseWatcher, WatcherRegistry
from colloquip.watchers.triage import MockTriageAgent

SUB_A = uuid4()
SUB_B = uuid4()


def make_config(**kwargs) -> WatcherConfig:
    defaults = dict(
        watcher_type=WatcherType.LITERATURE,
        subreddit_id=SUB_A,
        name="test_watcher",
        query="GLP-1 receptor agonists",
    )
    defaults.update(kwargs)
    return WatcherConfig(**defaults)


def make_event(watcher_id=None, title="New paper", summary="", **kwargs) -> WatcherEvent:
    defaults = dict(
        watcher_id=watcher_id or uuid4(),
        subreddit_id=SUB_A,
        title=title,
        summary=summary,
        source=WatcherSource(source_type="pubmed", source_id=str(uuid4())),
    )
    defaults.update(kwargs)
    return WatcherEvent(**defaults)


# --- WatcherRegistry ---


class TestWatcherRegistry:
    def test_register_and_get(self):
        class DummyWatcher(BaseWatcher):
            async def poll(self):
                return []

            async def validate_config(self):
                return True

        registry = WatcherRegistry()
        config = make_config()
        watcher = DummyWatcher(config)
        registry.register(watcher)

        assert registry.count() == 1
        assert registry.get(config.id) is watcher

    def test_unregister(self):
        class DummyWatcher(BaseWatcher):
            async def poll(self):
                return []

            async def validate_config(self):
                return True

        registry = WatcherRegistry()
        config = make_config()
        watcher = DummyWatcher(config)
        registry.register(watcher)
        registry.unregister(config.id)
        assert registry.count() == 0
        assert registry.get(config.id) is None

    def test_get_by_subreddit(self):
        class DummyWatcher(BaseWatcher):
            async def poll(self):
                return []

            async def validate_config(self):
                return True

        registry = WatcherRegistry()
        c1 = make_config(subreddit_id=SUB_A)
        c2 = make_config(subreddit_id=SUB_B)
        registry.register(DummyWatcher(c1))
        registry.register(DummyWatcher(c2))

        sub_a_watchers = registry.get_by_subreddit(SUB_A)
        assert len(sub_a_watchers) == 1

    def test_get_enabled(self):
        class DummyWatcher(BaseWatcher):
            async def poll(self):
                return []

            async def validate_config(self):
                return True

        registry = WatcherRegistry()
        c1 = make_config(enabled=True)
        c2 = make_config(enabled=False)
        registry.register(DummyWatcher(c1))
        registry.register(DummyWatcher(c2))

        enabled = registry.get_enabled()
        assert len(enabled) == 1

    def test_unregister_nonexistent(self):
        registry = WatcherRegistry()
        registry.unregister(uuid4())  # Should not raise
        assert registry.count() == 0


# --- MockTriageAgent ---


class TestMockTriageAgent:
    @pytest.fixture
    def triage(self):
        return MockTriageAgent()

    @pytest.fixture
    def config(self):
        return make_config(query="GLP-1 receptor agonists")

    @pytest.mark.asyncio
    async def test_first_event_is_novel(self, triage, config):
        event = make_event(
            title="Novel GLP-1 receptor agonist in diabetes",
            summary="A breakthrough study on GLP-1 receptor agonists.",
        )
        decision = await triage.evaluate(event, config)
        assert decision.novelty > 0.5
        assert decision.signal != TriageSignal.LOW

    @pytest.mark.asyncio
    async def test_duplicate_event_is_low(self, triage, config):
        event1 = make_event(title="Some paper", summary="Details")
        event2 = make_event(
            title="Some paper",
            summary="Details",
            source=WatcherSource(
                source_type="pubmed",
                source_id=event1.source.source_id,
            ),
        )
        decision = await triage.evaluate(event2, config, recent_events=[event1])
        assert decision.signal == TriageSignal.LOW
        assert "Duplicate" in decision.reasoning

    @pytest.mark.asyncio
    async def test_high_relevance_event(self, triage, config):
        event = make_event(
            title="GLP-1 receptor agonists breakthrough novel findings",
            summary="A breakthrough study on novel GLP-1 receptor agonists efficacy.",
        )
        decision = await triage.evaluate(event, config)
        assert decision.relevance > 0.5
        assert decision.signal in (TriageSignal.MEDIUM, TriageSignal.HIGH)

    @pytest.mark.asyncio
    async def test_low_relevance_event(self, triage, config):
        event = make_event(
            title="Unrelated topic about gardening",
            summary="How to grow tomatoes in your backyard.",
        )
        decision = await triage.evaluate(event, config, recent_events=[])
        assert decision.relevance < 0.3

    @pytest.mark.asyncio
    async def test_urgency_keywords(self, triage, config):
        event = make_event(
            title="Breakthrough novel discovery in GLP-1 agonists",
            summary="Critical finding on receptor binding.",
        )
        decision = await triage.evaluate(event, config)
        assert decision.urgency > 0.0

    @pytest.mark.asyncio
    async def test_suggested_hypothesis(self, triage, config):
        event = make_event(
            title="GLP-1 receptor agonists improve outcomes",
            summary="A relevant study.",
        )
        decision = await triage.evaluate(event, config)
        if decision.signal != TriageSignal.LOW:
            assert decision.suggested_hypothesis is not None
            assert "GLP-1" in decision.suggested_hypothesis

    @pytest.mark.asyncio
    async def test_novelty_decreases_with_similar_events(self, triage, config):
        recent = [
            make_event(title="Study on GLP-1 receptor binding"),
            make_event(title="GLP-1 receptor agonist effects"),
        ]
        event = make_event(title="GLP-1 receptor binding study")
        decision = await triage.evaluate(event, config, recent_events=recent)
        # Novelty should be lower due to overlap
        assert decision.novelty < 0.8

    @pytest.mark.asyncio
    async def test_duplicate_same_source_id(self, triage, config):
        source_id = "PMID:12345"
        event1 = make_event(
            title="Paper 1",
            source=WatcherSource(source_type="pubmed", source_id=source_id),
        )
        event2 = make_event(
            title="Paper 1 updated",
            source=WatcherSource(source_type="pubmed", source_id=source_id),
        )
        decision = await triage.evaluate(event2, config, recent_events=[event1])
        assert decision.signal == TriageSignal.LOW

    @pytest.mark.asyncio
    async def test_composite_scoring(self, triage, config):
        event = make_event(
            title="Completely unrelated garbanzo bean farming",
            summary="Not relevant at all to anything scientific.",
        )
        decision = await triage.evaluate(event, config)
        # Low relevance, moderate novelty, no urgency = low signal
        assert decision.signal == TriageSignal.LOW

    @pytest.mark.asyncio
    async def test_custom_thresholds(self, config):
        strict_triage = MockTriageAgent(high_threshold=0.95, medium_threshold=0.9)
        event = make_event(
            title="GLP-1 receptor agonists study",
            summary="Some relevant content.",
        )
        decision = await strict_triage.evaluate(event, config)
        # With very high thresholds, most events should be LOW
        assert decision.signal == TriageSignal.LOW

    @pytest.mark.asyncio
    async def test_reasoning_format(self, triage, config):
        event = make_event(
            title="GLP-1 receptor agonists in clinical trials",
            summary="Results from phase 3.",
        )
        decision = await triage.evaluate(event, config)
        assert "Composite score" in decision.reasoning

    @pytest.mark.asyncio
    async def test_empty_query_defaults_relevance(self, triage):
        config = make_config(query="")
        event = make_event(title="Some event")
        decision = await triage.evaluate(event, config)
        assert decision.relevance == 0.5


# --- WatcherConfig model ---


class TestWatcherModels:
    def test_watcher_config_defaults(self):
        config = make_config()
        assert config.enabled is True
        assert config.poll_interval_seconds == 300

    def test_watcher_event_creation(self):
        event = make_event(title="Test", summary="Description")
        assert event.title == "Test"
        assert event.summary == "Description"
        assert event.source.source_type == "pubmed"

    def test_watcher_source_with_metadata(self):
        source = WatcherSource(
            source_type="pubmed",
            source_id="PMID:12345",
            url="https://pubmed.ncbi.nlm.nih.gov/12345/",
            metadata={"year": 2026, "journal": "Nature"},
        )
        assert source.metadata["year"] == 2026
