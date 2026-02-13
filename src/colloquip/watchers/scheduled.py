"""Scheduled watcher: fires events on a configurable time-based schedule.

Supports interval-based triggering (every N hours/days) and optional
day-of-week / time-of-day constraints.
"""

import logging
from datetime import datetime, timezone
from typing import List, Optional

from colloquip.models import WatcherConfig, WatcherEvent, WatcherSource
from colloquip.watchers.interface import BaseWatcher

logger = logging.getLogger(__name__)


class ScheduledWatcher(BaseWatcher):
    """Fires events based on a time schedule.

    Config options (in config.config):
        interval_hours: Minimum hours between firings (default: 24)
        day_of_week: Optional list of days (0=Mon, 6=Sun) to restrict to
        time_of_day_utc: Optional hour (0-23) to fire at
        topic: Topic/title for the generated event
        description: Description for the generated event
    """

    def __init__(self, config: WatcherConfig):
        super().__init__(config)
        self._last_fired: Optional[datetime] = None
        self._interval_hours: float = config.config.get("interval_hours", 24.0)
        self._day_of_week: Optional[List[int]] = config.config.get("day_of_week")
        self._time_of_day_utc: Optional[int] = config.config.get("time_of_day_utc")
        self._topic: str = config.config.get("topic", config.name)
        self._description: str = config.config.get("description", config.description)

    async def poll(self) -> List[WatcherEvent]:
        """Check if it's time to fire a scheduled event."""
        now = datetime.now(timezone.utc)

        if not self._should_fire(now):
            return []

        self._last_fired = now

        event = WatcherEvent(
            watcher_id=self.watcher_id,
            subreddit_id=self.subreddit_id,
            title=f"Scheduled: {self._topic}",
            summary=self._description or f"Scheduled review of {self._topic}",
            source=WatcherSource(
                source_type="schedule",
                source_id=str(self.watcher_id),
                metadata={
                    "interval_hours": self._interval_hours,
                    "fired_at": now.isoformat(),
                },
            ),
        )

        logger.info("Scheduled watcher %s fired", self.config.name)
        return [event]

    def _should_fire(self, now: datetime) -> bool:
        """Determine if the watcher should fire at this time."""
        # Check interval
        if self._last_fired:
            elapsed_hours = (now - self._last_fired).total_seconds() / 3600
            if elapsed_hours < self._interval_hours:
                return False

        # Check day-of-week constraint
        if self._day_of_week is not None:
            if now.weekday() not in self._day_of_week:
                return False

        # Check time-of-day constraint
        if self._time_of_day_utc is not None:
            if now.hour != self._time_of_day_utc:
                return False

        return True

    async def validate_config(self) -> bool:
        """Validate schedule configuration."""
        if self._interval_hours <= 0:
            return False
        if self._day_of_week is not None:
            if not all(0 <= d <= 6 for d in self._day_of_week):
                return False
        if self._time_of_day_utc is not None:
            if not (0 <= self._time_of_day_utc <= 23):
                return False
        return True

    @property
    def last_fired(self) -> Optional[datetime]:
        return self._last_fired

    @last_fired.setter
    def last_fired(self, value: Optional[datetime]) -> None:
        self._last_fired = value
