"""Abstract base for event watchers and the watcher registry.

A watcher monitors an external source (literature database, schedule, webhook)
and produces WatcherEvent objects when something notable is detected.
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, List
from uuid import UUID

from colloquip.models import WatcherConfig, WatcherEvent

logger = logging.getLogger(__name__)


class BaseWatcher(ABC):
    """Abstract base for all event watchers.

    Subclasses implement poll() to check their source for new events.
    Each watcher is configured via a WatcherConfig and scoped to a subreddit.
    """

    def __init__(self, config: WatcherConfig):
        self.config = config

    @property
    def watcher_id(self) -> UUID:
        return self.config.id

    @property
    def subreddit_id(self) -> UUID:
        return self.config.subreddit_id

    @property
    def enabled(self) -> bool:
        return self.config.enabled

    @abstractmethod
    async def poll(self) -> List[WatcherEvent]:
        """Check the source for new events since last poll.

        Returns a list of new events (possibly empty).
        Implementations must track their own last-checked state.
        """
        ...

    @abstractmethod
    async def validate_config(self) -> bool:
        """Validate that the watcher configuration is correct.

        Returns True if config is valid and the watcher can operate.
        """
        ...


class WatcherRegistry:
    """Registry for active watcher instances.

    Tracks watchers by ID and provides lookup by subreddit.
    """

    def __init__(self) -> None:
        self._watchers: Dict[UUID, BaseWatcher] = {}

    def register(self, watcher: BaseWatcher) -> None:
        """Register a watcher instance."""
        self._watchers[watcher.watcher_id] = watcher
        logger.info(
            "Registered watcher %s (%s) for subreddit %s",
            watcher.config.name,
            watcher.config.watcher_type.value,
            watcher.subreddit_id,
        )

    def unregister(self, watcher_id: UUID) -> None:
        """Remove a watcher from the registry."""
        self._watchers.pop(watcher_id, None)

    def get(self, watcher_id: UUID) -> BaseWatcher | None:
        return self._watchers.get(watcher_id)

    def get_by_subreddit(self, subreddit_id: UUID) -> List[BaseWatcher]:
        """Get all watchers for a subreddit."""
        return [w for w in self._watchers.values() if w.subreddit_id == subreddit_id]

    def get_enabled(self) -> List[BaseWatcher]:
        """Get all enabled watchers."""
        return [w for w in self._watchers.values() if w.enabled]

    def count(self) -> int:
        return len(self._watchers)

    def all(self) -> List[BaseWatcher]:
        return list(self._watchers.values())
