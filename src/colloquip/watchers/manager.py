"""Watcher manager: orchestrates all watchers with polling loop.

Manages the event -> triage -> notification pipeline.
Each watcher is polled independently with error isolation.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Callable, Dict, List, Optional
from uuid import UUID

from colloquip.models import (
    Notification,
    TriageDecision,
    TriageSignal,
    WatcherConfig,
    WatcherEvent,
)
from colloquip.watchers.interface import BaseWatcher, WatcherRegistry
from colloquip.watchers.triage import TriageAgent

logger = logging.getLogger(__name__)

# Max recent events to keep per watcher (for dedup in triage)
_MAX_RECENT_EVENTS = 50


class WatcherManager:
    """Orchestrates watcher polling, triage, and notification generation.

    Runs an async polling loop that:
    1. Polls each enabled watcher
    2. Sends new events through the triage agent
    3. Generates notifications for medium/high-signal events
    4. Optionally calls a notification callback
    """

    def __init__(
        self,
        registry: WatcherRegistry,
        triage_agent: TriageAgent,
        poll_interval_seconds: float = 300.0,
        on_notification: Optional[Callable] = None,
    ):
        self.registry = registry
        self.triage_agent = triage_agent
        self.poll_interval_seconds = poll_interval_seconds
        self._on_notification = on_notification
        self._recent_events: Dict[UUID, List[WatcherEvent]] = {}
        self._triage_history: List[TriageDecision] = []
        self._notifications: List[Notification] = []
        self._running = False
        self._task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        """Start the polling loop as a background task."""
        if self._running:
            logger.warning("WatcherManager already running")
            return
        self._running = True
        self._task = asyncio.create_task(self._poll_loop())
        logger.info("WatcherManager started (interval=%ss)", self.poll_interval_seconds)

    async def stop(self) -> None:
        """Stop the polling loop."""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self._task = None
        logger.info("WatcherManager stopped")

    async def poll_once(self) -> List[Notification]:
        """Run a single polling cycle across all enabled watchers.

        Returns notifications generated in this cycle.
        """
        notifications = []
        watchers = self.registry.get_enabled()

        for watcher in watchers:
            try:
                new_notifs = await self._poll_watcher(watcher)
                notifications.extend(new_notifs)
            except Exception as e:
                logger.error(
                    "Error polling watcher %s (%s): %s",
                    watcher.config.name, watcher.watcher_id, e,
                )

        return notifications

    async def _poll_loop(self) -> None:
        """Internal polling loop."""
        while self._running:
            try:
                await self.poll_once()
            except Exception as e:
                logger.error("Polling cycle error: %s", e)
            try:
                await asyncio.sleep(self.poll_interval_seconds)
            except asyncio.CancelledError:
                break

    async def _poll_watcher(self, watcher: BaseWatcher) -> List[Notification]:
        """Poll a single watcher and process its events."""
        events = await watcher.poll()
        if not events:
            return []

        # Get recent events for dedup
        recent = self._recent_events.get(watcher.watcher_id, [])

        notifications = []
        for event in events:
            # Run triage
            decision = await self.triage_agent.evaluate(
                event=event,
                watcher_config=watcher.config,
                recent_events=recent,
            )
            self._triage_history.append(decision)

            # Track for dedup
            recent.append(event)

            # Generate notification for medium/high signals
            if decision.signal in (TriageSignal.MEDIUM, TriageSignal.HIGH):
                notification = Notification(
                    watcher_id=watcher.watcher_id,
                    event_id=event.id,
                    subreddit_id=watcher.subreddit_id,
                    title=event.title,
                    summary=decision.reasoning,
                    signal=decision.signal,
                    suggested_hypothesis=decision.suggested_hypothesis,
                )
                notifications.append(notification)
                self._notifications.append(notification)

                if self._on_notification:
                    try:
                        await self._on_notification(notification)
                    except Exception as e:
                        logger.error("Notification callback error: %s", e)

        # Trim recent events
        if len(recent) > _MAX_RECENT_EVENTS:
            recent = recent[-_MAX_RECENT_EVENTS:]
        self._recent_events[watcher.watcher_id] = recent

        return notifications

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def triage_history(self) -> List[TriageDecision]:
        return list(self._triage_history)

    @property
    def notifications(self) -> List[Notification]:
        return list(self._notifications)

    def get_notifications_by_subreddit(self, subreddit_id: UUID) -> List[Notification]:
        """Get all notifications for a subreddit."""
        return [n for n in self._notifications if n.subreddit_id == subreddit_id]
