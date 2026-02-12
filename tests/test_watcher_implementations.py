"""Tests for concrete watcher implementations: literature, scheduled, webhook."""

from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from colloquip.models import WatcherConfig, WatcherType
from colloquip.tools.interface import SearchResult, ToolResult
from colloquip.watchers.literature import LiteratureWatcher
from colloquip.watchers.scheduled import ScheduledWatcher
from colloquip.watchers.webhook import WebhookWatcher


SUB_A = uuid4()


def make_config(watcher_type=WatcherType.LITERATURE, **kwargs) -> WatcherConfig:
    defaults = dict(
        watcher_type=watcher_type,
        subreddit_id=SUB_A,
        name="test_watcher",
        query="GLP-1 receptor agonists",
    )
    defaults.update(kwargs)
    return WatcherConfig(**defaults)


def make_search_result(source_id="PMID:001", title="Paper Title") -> SearchResult:
    return SearchResult(
        title=title,
        authors=["Author A", "Author B"],
        abstract="Abstract text here.",
        url=f"https://pubmed.ncbi.nlm.nih.gov/{source_id}/",
        source_id=source_id,
        source_type="pubmed",
        year=2026,
    )


# --- LiteratureWatcher ---

class TestLiteratureWatcher:
    @pytest.fixture
    def mock_pubmed(self):
        tool = AsyncMock()
        tool.execute = AsyncMock(return_value=ToolResult(
            source="pubmed",
            query="GLP-1",
            results=[
                make_search_result("PMID:001", "GLP-1 study 1"),
                make_search_result("PMID:002", "GLP-1 study 2"),
            ],
        ))
        return tool

    @pytest.mark.asyncio
    async def test_poll_returns_events(self, mock_pubmed):
        config = make_config()
        watcher = LiteratureWatcher(config, pubmed_tool=mock_pubmed)
        events = await watcher.poll()
        assert len(events) == 2
        assert events[0].title == "GLP-1 study 1"
        assert events[0].source.source_type == "pubmed"
        assert events[0].source.source_id == "PMID:001"

    @pytest.mark.asyncio
    async def test_deduplication(self, mock_pubmed):
        config = make_config()
        watcher = LiteratureWatcher(config, pubmed_tool=mock_pubmed)

        events1 = await watcher.poll()
        assert len(events1) == 2
        assert watcher.seen_count == 2

        # Second poll should deduplicate
        events2 = await watcher.poll()
        assert len(events2) == 0

    @pytest.mark.asyncio
    async def test_new_papers_after_seen(self, mock_pubmed):
        config = make_config()
        watcher = LiteratureWatcher(config, pubmed_tool=mock_pubmed)

        await watcher.poll()  # Sees PMID:001, PMID:002

        # Return new paper
        mock_pubmed.execute.return_value = ToolResult(
            source="pubmed",
            query="GLP-1",
            results=[
                make_search_result("PMID:001", "Old paper"),
                make_search_result("PMID:003", "New paper"),
            ],
        )
        events = await watcher.poll()
        assert len(events) == 1
        assert events[0].source.source_id == "PMID:003"

    @pytest.mark.asyncio
    async def test_no_query_returns_empty(self):
        config = make_config(query="")
        watcher = LiteratureWatcher(config, pubmed_tool=AsyncMock())
        events = await watcher.poll()
        assert events == []

    @pytest.mark.asyncio
    async def test_no_pubmed_tool(self):
        config = make_config()
        watcher = LiteratureWatcher(config, pubmed_tool=None)
        events = await watcher.poll()
        assert events == []

    @pytest.mark.asyncio
    async def test_pubmed_error(self, mock_pubmed):
        mock_pubmed.execute.return_value = ToolResult(
            source="pubmed", query="GLP-1", results=[], error="API error"
        )
        config = make_config()
        watcher = LiteratureWatcher(config, pubmed_tool=mock_pubmed)
        events = await watcher.poll()
        assert events == []

    @pytest.mark.asyncio
    async def test_validate_config(self, mock_pubmed):
        config = make_config(query="some query")
        watcher = LiteratureWatcher(config, pubmed_tool=mock_pubmed)
        assert await watcher.validate_config() is True

    @pytest.mark.asyncio
    async def test_validate_config_no_query(self, mock_pubmed):
        config = make_config(query="")
        watcher = LiteratureWatcher(config, pubmed_tool=mock_pubmed)
        assert await watcher.validate_config() is False

    @pytest.mark.asyncio
    async def test_last_checked(self, mock_pubmed):
        config = make_config()
        watcher = LiteratureWatcher(config, pubmed_tool=mock_pubmed)
        assert watcher.last_checked is None
        await watcher.poll()
        assert watcher.last_checked is not None


# --- ScheduledWatcher ---

class TestScheduledWatcher:
    @pytest.mark.asyncio
    async def test_fires_on_first_poll(self):
        config = make_config(
            watcher_type=WatcherType.SCHEDULED,
            config={"interval_hours": 24, "topic": "Weekly review"},
        )
        watcher = ScheduledWatcher(config)
        events = await watcher.poll()
        assert len(events) == 1
        assert "Weekly review" in events[0].title

    @pytest.mark.asyncio
    async def test_respects_interval(self):
        config = make_config(
            watcher_type=WatcherType.SCHEDULED,
            config={"interval_hours": 24},
        )
        watcher = ScheduledWatcher(config)

        events1 = await watcher.poll()
        assert len(events1) == 1

        # Immediate re-poll should not fire
        events2 = await watcher.poll()
        assert len(events2) == 0

    @pytest.mark.asyncio
    async def test_fires_after_interval(self):
        config = make_config(
            watcher_type=WatcherType.SCHEDULED,
            config={"interval_hours": 1},
        )
        watcher = ScheduledWatcher(config)
        await watcher.poll()

        # Simulate time passing
        watcher.last_fired = datetime.now(timezone.utc) - timedelta(hours=2)
        events = await watcher.poll()
        assert len(events) == 1

    @pytest.mark.asyncio
    async def test_day_of_week_constraint(self):
        config = make_config(
            watcher_type=WatcherType.SCHEDULED,
            config={"interval_hours": 1, "day_of_week": [99]},  # Invalid day
        )
        watcher = ScheduledWatcher(config)
        events = await watcher.poll()
        assert len(events) == 0

    @pytest.mark.asyncio
    async def test_time_of_day_constraint(self):
        config = make_config(
            watcher_type=WatcherType.SCHEDULED,
            config={"interval_hours": 1, "time_of_day_utc": 99},  # Invalid hour
        )
        watcher = ScheduledWatcher(config)
        events = await watcher.poll()
        assert len(events) == 0

    @pytest.mark.asyncio
    async def test_validate_config_valid(self):
        config = make_config(
            watcher_type=WatcherType.SCHEDULED,
            config={"interval_hours": 24},
        )
        watcher = ScheduledWatcher(config)
        assert await watcher.validate_config() is True

    @pytest.mark.asyncio
    async def test_validate_config_invalid_interval(self):
        config = make_config(
            watcher_type=WatcherType.SCHEDULED,
            config={"interval_hours": -1},
        )
        watcher = ScheduledWatcher(config)
        assert await watcher.validate_config() is False

    @pytest.mark.asyncio
    async def test_validate_config_invalid_day(self):
        config = make_config(
            watcher_type=WatcherType.SCHEDULED,
            config={"interval_hours": 24, "day_of_week": [7]},
        )
        watcher = ScheduledWatcher(config)
        assert await watcher.validate_config() is False


# --- WebhookWatcher ---

class TestWebhookWatcher:
    @pytest.mark.asyncio
    async def test_receive_and_poll(self):
        config = make_config(watcher_type=WatcherType.WEBHOOK)
        watcher = WebhookWatcher(config)

        event = watcher.receive_webhook(
            {"title": "External finding", "summary": "Important data"},
            sender="external_system",
        )
        assert event is not None
        assert event.title == "External finding"

        events = await watcher.poll()
        assert len(events) == 1
        assert events[0].title == "External finding"

        # Buffer should be cleared after poll
        events2 = await watcher.poll()
        assert len(events2) == 0

    @pytest.mark.asyncio
    async def test_reject_no_title(self):
        config = make_config(watcher_type=WatcherType.WEBHOOK)
        watcher = WebhookWatcher(config)
        result = watcher.receive_webhook({"summary": "No title"})
        assert result is None
        assert watcher.buffer_size == 0

    @pytest.mark.asyncio
    async def test_allowed_senders(self):
        config = make_config(
            watcher_type=WatcherType.WEBHOOK,
            config={"allowed_senders": ["trusted_source"]},
        )
        watcher = WebhookWatcher(config)

        # Trusted sender
        event = watcher.receive_webhook(
            {"title": "Good event"}, sender="trusted_source"
        )
        assert event is not None

        # Untrusted sender
        event2 = watcher.receive_webhook(
            {"title": "Bad event"}, sender="untrusted"
        )
        assert event2 is None
        assert watcher.buffer_size == 1  # Only the trusted event

    @pytest.mark.asyncio
    async def test_webhook_metadata_captured(self):
        config = make_config(watcher_type=WatcherType.WEBHOOK)
        watcher = WebhookWatcher(config)

        event = watcher.receive_webhook({
            "title": "Finding",
            "summary": "Details",
            "url": "https://example.com",
            "custom_field": "value",
        })
        assert event.source.source_type == "webhook"
        assert event.source.url == "https://example.com"
        assert event.raw_data["custom_field"] == "value"

    @pytest.mark.asyncio
    async def test_validate_config(self):
        config = make_config(watcher_type=WatcherType.WEBHOOK)
        watcher = WebhookWatcher(config)
        assert await watcher.validate_config() is True

    @pytest.mark.asyncio
    async def test_multiple_webhooks(self):
        config = make_config(watcher_type=WatcherType.WEBHOOK)
        watcher = WebhookWatcher(config)

        for i in range(5):
            watcher.receive_webhook({"title": f"Event {i}"})

        assert watcher.buffer_size == 5
        events = await watcher.poll()
        assert len(events) == 5
        assert watcher.buffer_size == 0
