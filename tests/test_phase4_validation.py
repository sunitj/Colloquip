"""Phase 4 validation: end-to-end tests for the event-driven trigger system."""

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from colloquip.models import (
    Notification,
    NotificationAction,
    NotificationStatus,
    TriageSignal,
    WatcherConfig,
    WatcherType,
)
from colloquip.notifications.store import InMemoryNotificationStore
from colloquip.tools.interface import SearchResult, ToolResult
from colloquip.watchers.auto_deliberation import AutoDeliberationPolicy
from colloquip.watchers.interface import BaseWatcher, WatcherRegistry
from colloquip.watchers.literature import LiteratureWatcher
from colloquip.watchers.manager import WatcherManager
from colloquip.watchers.scheduled import ScheduledWatcher
from colloquip.watchers.triage import MockTriageAgent
from colloquip.watchers.webhook import WebhookWatcher

SUB_A = uuid4()


class TestPhase4EndToEnd:
    """End-to-end validation of the Phase 4 pipeline:
    watcher -> event -> triage -> notification -> action
    """

    @pytest.mark.asyncio
    async def test_full_pipeline_literature(self):
        """Literature watcher -> triage -> notification -> create thread."""
        # Set up mock PubMed tool
        mock_pubmed = AsyncMock()
        mock_pubmed.execute = AsyncMock(
            return_value=ToolResult(
                source="pubmed",
                query="GLP-1",
                results=[
                    SearchResult(
                        title="Breakthrough novel GLP-1 receptor agonist findings",
                        authors=["Smith", "Jones"],
                        abstract="A critical breakthrough study demonstrating novel effects.",
                        url="https://pubmed.ncbi.nlm.nih.gov/99999/",
                        source_id="PMID:99999",
                        source_type="pubmed",
                        year=2026,
                    ),
                ],
            )
        )

        # Set up watcher
        config = WatcherConfig(
            watcher_type=WatcherType.LITERATURE,
            subreddit_id=SUB_A,
            name="GLP-1 monitor",
            query="GLP-1 breakthrough novel receptor agonist",
        )
        watcher = LiteratureWatcher(config, pubmed_tool=mock_pubmed)

        # Set up triage and manager
        registry = WatcherRegistry()
        registry.register(watcher)
        triage = MockTriageAgent()

        received_notifications = []

        async def on_notif(n):
            received_notifications.append(n)

        manager = WatcherManager(
            registry=registry,
            triage_agent=triage,
            on_notification=on_notif,
        )

        # Run polling
        notifications = await manager.poll_once()

        # Verify triage happened
        assert len(manager.triage_history) == 1
        decision = manager.triage_history[0]
        assert decision.relevance > 0.0

        # If notification was generated, verify it
        if notifications:
            notif = notifications[0]
            assert notif.subreddit_id == SUB_A
            assert notif.signal in (TriageSignal.MEDIUM, TriageSignal.HIGH)
            assert len(received_notifications) > 0

    @pytest.mark.asyncio
    async def test_full_pipeline_webhook(self):
        """Webhook -> event -> triage -> notification."""
        config = WatcherConfig(
            watcher_type=WatcherType.WEBHOOK,
            subreddit_id=SUB_A,
            name="external_data",
            query="breakthrough novel clinical trial results",
        )
        webhook = WebhookWatcher(config)
        registry = WatcherRegistry()
        registry.register(webhook)

        # Receive webhook
        webhook.receive_webhook(
            {
                "title": "Breakthrough novel clinical trial results for receptor agonist",
                "summary": "Phase 3 trial showed breakthrough novel efficacy.",
                "url": "https://clinicaltrials.gov/ct2/show/NCT99999",
            }
        )

        # Run triage
        triage = MockTriageAgent()
        manager = WatcherManager(registry=registry, triage_agent=triage)
        await manager.poll_once()

        assert len(manager.triage_history) == 1

    @pytest.mark.asyncio
    async def test_full_pipeline_scheduled(self):
        """Scheduled watcher -> event -> triage."""
        config = WatcherConfig(
            watcher_type=WatcherType.SCHEDULED,
            subreddit_id=SUB_A,
            name="weekly_review",
            query="receptor agonists",
            config={"interval_hours": 24, "topic": "Weekly GLP-1 review"},
        )
        scheduled = ScheduledWatcher(config)
        registry = WatcherRegistry()
        registry.register(scheduled)

        triage = MockTriageAgent()
        manager = WatcherManager(registry=registry, triage_agent=triage)
        await manager.poll_once()

        assert len(manager.triage_history) == 1
        # Scheduled events are typically medium relevance
        decision = manager.triage_history[0]
        assert decision.event_id is not None

    @pytest.mark.asyncio
    async def test_notification_acted_upon(self):
        """User acts on a notification by creating a thread."""
        store = InMemoryNotificationStore()
        notif = Notification(
            watcher_id=uuid4(),
            event_id=uuid4(),
            subreddit_id=SUB_A,
            title="New relevant paper detected",
            summary="High relevance to current research.",
            signal=TriageSignal.HIGH,
            suggested_hypothesis="Evaluate the implications of the new findings.",
        )
        await store.save(notif)

        # User creates thread
        thread_id = uuid4()
        await store.act(notif.id, NotificationAction.CREATE_THREAD, thread_id=thread_id)

        result = await store.get(notif.id)
        assert result.status == NotificationStatus.ACTED
        assert result.action_taken == NotificationAction.CREATE_THREAD
        assert result.thread_id == thread_id

    @pytest.mark.asyncio
    async def test_auto_deliberation_integration(self):
        """Auto-deliberation policy integrates with watcher manager."""
        policy = AutoDeliberationPolicy(
            min_events=5,
            min_useful_rate=0.5,
            max_threads_per_hour=3,
        )
        watcher_id = uuid4()
        policy.approve_watcher(watcher_id)

        # Simulate processing events
        for _ in range(10):
            policy.record_event(watcher_id)
        for _ in range(8):
            policy.record_useful_outcome(watcher_id)

        check = policy.can_auto_create(watcher_id)
        assert check.allowed

        # Record auto-thread
        policy.record_auto_thread(watcher_id)
        stats = policy.get_stats(watcher_id)
        assert stats["auto_threads_created"] == 1

    @pytest.mark.asyncio
    async def test_deduplication_across_polls(self):
        """Events are deduplicated across consecutive polls."""
        mock_pubmed = AsyncMock()
        mock_pubmed.execute = AsyncMock(
            return_value=ToolResult(
                source="pubmed",
                query="test",
                results=[
                    SearchResult(
                        title="Paper A",
                        source_id="PMID:001",
                        source_type="pubmed",
                    ),
                ],
            )
        )

        config = WatcherConfig(
            watcher_type=WatcherType.LITERATURE,
            subreddit_id=SUB_A,
            name="test",
            query="test",
        )
        watcher = LiteratureWatcher(config, pubmed_tool=mock_pubmed)
        registry = WatcherRegistry()
        registry.register(watcher)

        triage = MockTriageAgent()
        manager = WatcherManager(registry=registry, triage_agent=triage)

        # First poll: 1 event
        await manager.poll_once()
        assert len(manager.triage_history) == 1

        # Second poll: same paper, deduped by watcher
        await manager.poll_once()
        assert len(manager.triage_history) == 1  # No new triage

    @pytest.mark.asyncio
    async def test_multiple_watchers_same_subreddit(self):
        """Multiple watchers can monitor the same subreddit."""
        registry = WatcherRegistry()
        triage = MockTriageAgent()

        for i in range(3):
            config = WatcherConfig(
                watcher_type=WatcherType.WEBHOOK,
                subreddit_id=SUB_A,
                name=f"webhook_{i}",
            )
            watcher = WebhookWatcher(config)
            watcher.receive_webhook({"title": f"Event from source {i}"})
            registry.register(watcher)

        manager = WatcherManager(registry=registry, triage_agent=triage)
        await manager.poll_once()

        assert len(manager.triage_history) == 3

    @pytest.mark.asyncio
    async def test_watcher_error_doesnt_block_others(self):
        """A failing watcher doesn't prevent others from running."""

        class FailingWatcher(BaseWatcher):
            async def poll(self):
                raise RuntimeError("Boom!")

            async def validate_config(self):
                return True

        registry = WatcherRegistry()
        fail_config = WatcherConfig(
            watcher_type=WatcherType.LITERATURE,
            subreddit_id=SUB_A,
            name="failing",
        )
        good_config = WatcherConfig(
            watcher_type=WatcherType.WEBHOOK,
            subreddit_id=SUB_A,
            name="good",
        )
        good_watcher = WebhookWatcher(good_config)
        good_watcher.receive_webhook({"title": "Good event"})

        registry.register(FailingWatcher(fail_config))
        registry.register(good_watcher)

        triage = MockTriageAgent()
        manager = WatcherManager(registry=registry, triage_agent=triage)
        await manager.poll_once()

        # Good watcher's event was still processed
        assert len(manager.triage_history) == 1
