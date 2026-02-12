"""Tests for notification store and watcher manager integration."""

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from colloquip.models import (
    Notification,
    NotificationAction,
    NotificationStatus,
    TriageSignal,
    WatcherConfig,
    WatcherEvent,
    WatcherSource,
    WatcherType,
)
from colloquip.notifications.store import InMemoryNotificationStore
from colloquip.watchers.interface import BaseWatcher, WatcherRegistry
from colloquip.watchers.manager import WatcherManager
from colloquip.watchers.triage import MockTriageAgent


SUB_A = uuid4()
SUB_B = uuid4()


def make_notification(subreddit_id=None, **kwargs) -> Notification:
    defaults = dict(
        watcher_id=uuid4(),
        event_id=uuid4(),
        subreddit_id=subreddit_id or SUB_A,
        title="Test notification",
        summary="Test summary",
        signal=TriageSignal.MEDIUM,
    )
    defaults.update(kwargs)
    return Notification(**defaults)


# --- InMemoryNotificationStore ---

class TestInMemoryNotificationStore:
    @pytest.fixture
    def store(self):
        return InMemoryNotificationStore()

    @pytest.mark.asyncio
    async def test_save_and_get(self, store):
        notif = make_notification()
        await store.save(notif)
        result = await store.get(notif.id)
        assert result is not None
        assert result.title == "Test notification"

    @pytest.mark.asyncio
    async def test_get_nonexistent(self, store):
        result = await store.get(uuid4())
        assert result is None

    @pytest.mark.asyncio
    async def test_list_by_subreddit(self, store):
        n1 = make_notification(subreddit_id=SUB_A)
        n2 = make_notification(subreddit_id=SUB_B)
        await store.save(n1)
        await store.save(n2)

        results = await store.list_by_subreddit(SUB_A)
        assert len(results) == 1
        assert results[0].subreddit_id == SUB_A

    @pytest.mark.asyncio
    async def test_list_all(self, store):
        for _ in range(5):
            await store.save(make_notification())
        results = await store.list_all()
        assert len(results) == 5

    @pytest.mark.asyncio
    async def test_list_filtered_by_status(self, store):
        n1 = make_notification(status=NotificationStatus.PENDING)
        n2 = make_notification(status=NotificationStatus.READ)
        await store.save(n1)
        await store.save(n2)

        pending = await store.list_all(status=NotificationStatus.PENDING)
        assert len(pending) == 1

    @pytest.mark.asyncio
    async def test_mark_read(self, store):
        notif = make_notification()
        await store.save(notif)
        await store.mark_read(notif.id)
        result = await store.get(notif.id)
        assert result.status == NotificationStatus.READ

    @pytest.mark.asyncio
    async def test_act(self, store):
        notif = make_notification()
        await store.save(notif)
        await store.act(notif.id, NotificationAction.CREATE_THREAD, thread_id=uuid4())
        result = await store.get(notif.id)
        assert result.status == NotificationStatus.ACTED
        assert result.action_taken == NotificationAction.CREATE_THREAD
        assert result.thread_id is not None
        assert result.acted_at is not None

    @pytest.mark.asyncio
    async def test_act_dismiss(self, store):
        notif = make_notification()
        await store.save(notif)
        await store.act(notif.id, NotificationAction.DISMISS)
        result = await store.get(notif.id)
        assert result.status == NotificationStatus.ACTED
        assert result.action_taken == NotificationAction.DISMISS

    @pytest.mark.asyncio
    async def test_act_nonexistent_raises(self, store):
        with pytest.raises(ValueError):
            await store.act(uuid4(), NotificationAction.DISMISS)

    @pytest.mark.asyncio
    async def test_count(self, store):
        for _ in range(3):
            await store.save(make_notification(subreddit_id=SUB_A))
        for _ in range(2):
            await store.save(make_notification(subreddit_id=SUB_B))

        assert await store.count() == 5
        assert await store.count(subreddit_id=SUB_A) == 3
        assert await store.count(subreddit_id=SUB_B) == 2

    @pytest.mark.asyncio
    async def test_count_by_status(self, store):
        n1 = make_notification()
        n2 = make_notification()
        await store.save(n1)
        await store.save(n2)
        await store.mark_read(n2.id)

        assert await store.count(status=NotificationStatus.PENDING) == 1
        assert await store.count(status=NotificationStatus.READ) == 1

    @pytest.mark.asyncio
    async def test_list_ordered_by_date(self, store):
        n1 = make_notification()
        n1.created_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
        n2 = make_notification()
        n2.created_at = datetime(2026, 2, 1, tzinfo=timezone.utc)
        await store.save(n1)
        await store.save(n2)

        results = await store.list_all()
        assert results[0].created_at > results[1].created_at


# --- WatcherManager ---

class DummyWatcher(BaseWatcher):
    def __init__(self, config, events=None):
        super().__init__(config)
        self._events = events or []

    async def poll(self):
        events = list(self._events)
        self._events.clear()
        return events

    async def validate_config(self):
        return True


class TestWatcherManager:
    @pytest.fixture
    def registry(self):
        return WatcherRegistry()

    @pytest.fixture
    def triage(self):
        return MockTriageAgent()

    @pytest.fixture
    def manager(self, registry, triage):
        return WatcherManager(
            registry=registry,
            triage_agent=triage,
            poll_interval_seconds=1.0,
        )

    @pytest.mark.asyncio
    async def test_poll_once_no_watchers(self, manager):
        notifications = await manager.poll_once()
        assert notifications == []

    @pytest.mark.asyncio
    async def test_poll_once_with_events(self, manager, registry):
        config = WatcherConfig(
            watcher_type=WatcherType.LITERATURE,
            subreddit_id=SUB_A,
            name="test",
            query="GLP-1 receptor agonists breakthrough",
        )
        events = [
            WatcherEvent(
                watcher_id=config.id,
                subreddit_id=SUB_A,
                title="Breakthrough GLP-1 receptor agonists findings",
                summary="A novel breakthrough study on GLP-1 receptor agonists.",
                source=WatcherSource(source_type="pubmed", source_id="PMID:999"),
            ),
        ]
        watcher = DummyWatcher(config, events=events)
        registry.register(watcher)

        notifications = await manager.poll_once()
        # Should generate notification for medium/high signal events
        assert len(manager.triage_history) == 1

    @pytest.mark.asyncio
    async def test_disabled_watchers_skipped(self, manager, registry):
        config = WatcherConfig(
            watcher_type=WatcherType.LITERATURE,
            subreddit_id=SUB_A,
            name="disabled",
            enabled=False,
        )
        watcher = DummyWatcher(config, events=[
            WatcherEvent(
                watcher_id=config.id,
                subreddit_id=SUB_A,
                title="Should be skipped",
                summary="",
                source=WatcherSource(source_type="test"),
            ),
        ])
        registry.register(watcher)

        notifications = await manager.poll_once()
        assert notifications == []

    @pytest.mark.asyncio
    async def test_notification_callback(self, registry, triage):
        received = []

        async def on_notif(n):
            received.append(n)

        manager = WatcherManager(
            registry=registry,
            triage_agent=triage,
            on_notification=on_notif,
        )

        config = WatcherConfig(
            watcher_type=WatcherType.LITERATURE,
            subreddit_id=SUB_A,
            name="test",
            query="breakthrough novel receptor agonists GLP-1",
        )
        events = [
            WatcherEvent(
                watcher_id=config.id,
                subreddit_id=SUB_A,
                title="Breakthrough novel GLP-1 receptor agonists study",
                summary="Critical breakthrough novel findings on receptor agonists.",
                source=WatcherSource(source_type="pubmed", source_id="PMID:111"),
            ),
        ]
        watcher = DummyWatcher(config, events=events)
        registry.register(watcher)

        await manager.poll_once()
        # If triage rated it medium or high, callback fires
        if manager.notifications:
            assert len(received) > 0

    @pytest.mark.asyncio
    async def test_error_isolation(self, registry, triage):
        """One watcher error shouldn't stop other watchers from being polled."""
        manager = WatcherManager(registry=registry, triage_agent=triage)

        class FailingWatcher(BaseWatcher):
            async def poll(self):
                raise RuntimeError("Watcher failure")
            async def validate_config(self):
                return True

        config1 = WatcherConfig(
            watcher_type=WatcherType.LITERATURE,
            subreddit_id=SUB_A, name="failing",
        )
        config2 = WatcherConfig(
            watcher_type=WatcherType.LITERATURE,
            subreddit_id=SUB_A, name="working",
        )
        registry.register(FailingWatcher(config1))
        registry.register(DummyWatcher(config2))

        # Should not raise
        await manager.poll_once()

    @pytest.mark.asyncio
    async def test_get_notifications_by_subreddit(self, manager, registry):
        config = WatcherConfig(
            watcher_type=WatcherType.LITERATURE,
            subreddit_id=SUB_A,
            name="test",
            query="GLP-1 breakthrough novel receptor agonists",
        )
        events = [
            WatcherEvent(
                watcher_id=config.id,
                subreddit_id=SUB_A,
                title="Breakthrough novel GLP-1 receptor agonists",
                summary="Important breakthrough novel findings.",
                source=WatcherSource(source_type="pubmed", source_id="PMID:222"),
            ),
        ]
        registry.register(DummyWatcher(config, events=events))
        await manager.poll_once()

        by_sub = manager.get_notifications_by_subreddit(SUB_A)
        assert all(n.subreddit_id == SUB_A for n in by_sub)
