"""Auto-deliberation policy: earned automation for watcher-triggered threads.

Auto-deliberation is a privilege that must be earned through demonstrated
value. Requirements:
1. Watcher has processed 20+ events
2. >70% of triage decisions led to useful outcomes
3. Human has explicitly approved auto-deliberation for this watcher
4. Rate limit: max 5 auto-threads per hour per watcher
5. Budget: shares the subreddit's monthly budget
"""

import logging
from collections import defaultdict
from datetime import datetime, timezone
from typing import Dict, List, Optional
from uuid import UUID

logger = logging.getLogger(__name__)

# Policy constants
MIN_EVENTS_REQUIRED = 20
MIN_USEFUL_RATE = 0.70
MAX_AUTO_THREADS_PER_HOUR = 5
DEFAULT_MAX_COST_PER_THREAD_USD = 5.0


class AutoDeliberationPolicy:
    """Evaluates whether a watcher has earned auto-deliberation privileges.

    Tracks per-watcher metrics and enforces rate limits.
    Auto-threads are always tagged for human review.
    """

    def __init__(
        self,
        min_events: int = MIN_EVENTS_REQUIRED,
        min_useful_rate: float = MIN_USEFUL_RATE,
        max_threads_per_hour: int = MAX_AUTO_THREADS_PER_HOUR,
        max_cost_per_thread_usd: float = DEFAULT_MAX_COST_PER_THREAD_USD,
    ):
        self.min_events = min_events
        self.min_useful_rate = min_useful_rate
        self.max_threads_per_hour = max_threads_per_hour
        self.max_cost_per_thread_usd = max_cost_per_thread_usd

        # Per-watcher state
        self._approved_watchers: set[UUID] = set()
        self._event_counts: Dict[UUID, int] = defaultdict(int)
        self._useful_counts: Dict[UUID, int] = defaultdict(int)
        self._auto_thread_times: Dict[UUID, List[datetime]] = defaultdict(list)

    def approve_watcher(self, watcher_id: UUID) -> None:
        """Explicitly approve a watcher for auto-deliberation."""
        self._approved_watchers.add(watcher_id)
        logger.info("Watcher %s approved for auto-deliberation", watcher_id)

    def revoke_watcher(self, watcher_id: UUID) -> None:
        """Revoke auto-deliberation approval for a watcher."""
        self._approved_watchers.discard(watcher_id)
        logger.info("Watcher %s auto-deliberation revoked", watcher_id)

    def record_event(self, watcher_id: UUID) -> None:
        """Record that a watcher has processed an event."""
        self._event_counts[watcher_id] += 1

    def record_useful_outcome(self, watcher_id: UUID) -> None:
        """Record that a watcher's event led to a useful outcome."""
        self._useful_counts[watcher_id] += 1

    def can_auto_create(
        self,
        watcher_id: UUID,
        now: Optional[datetime] = None,
    ) -> "AutoDeliberationCheck":
        """Check if a watcher can auto-create a deliberation thread.

        Returns an AutoDeliberationCheck with the result and reasoning.
        """
        now = now or datetime.now(timezone.utc)
        reasons: List[str] = []

        # Check 1: Human approval
        if watcher_id not in self._approved_watchers:
            reasons.append("Not approved for auto-deliberation")

        # Check 2: Minimum events processed
        event_count = self._event_counts.get(watcher_id, 0)
        if event_count < self.min_events:
            reasons.append(f"Only {event_count}/{self.min_events} events processed")

        # Check 3: Useful outcome rate
        useful_count = self._useful_counts.get(watcher_id, 0)
        if event_count > 0:
            useful_rate = useful_count / event_count
        else:
            useful_rate = 0.0
        if useful_rate < self.min_useful_rate:
            reasons.append(f"Useful rate {useful_rate:.0%} < {self.min_useful_rate:.0%} required")

        # Check 4: Rate limit
        recent_threads = self._auto_thread_times.get(watcher_id, [])
        one_hour_ago = now.timestamp() - 3600
        recent_in_hour = [t for t in recent_threads if t.timestamp() > one_hour_ago]
        if len(recent_in_hour) >= self.max_threads_per_hour:
            reasons.append(
                f"Rate limit: {len(recent_in_hour)}/{self.max_threads_per_hour} "
                f"auto-threads in the last hour"
            )

        allowed = len(reasons) == 0
        return AutoDeliberationCheck(
            allowed=allowed,
            watcher_id=watcher_id,
            event_count=event_count,
            useful_rate=useful_rate,
            recent_auto_threads=len(recent_in_hour),
            reasons=reasons,
        )

    def record_auto_thread(self, watcher_id: UUID, now: Optional[datetime] = None) -> None:
        """Record that an auto-thread was created."""
        now = now or datetime.now(timezone.utc)
        self._auto_thread_times[watcher_id].append(now)

    def get_stats(self, watcher_id: UUID) -> Dict:
        """Get auto-deliberation stats for a watcher."""
        event_count = self._event_counts.get(watcher_id, 0)
        useful_count = self._useful_counts.get(watcher_id, 0)
        return {
            "watcher_id": str(watcher_id),
            "approved": watcher_id in self._approved_watchers,
            "events_processed": event_count,
            "useful_outcomes": useful_count,
            "useful_rate": useful_count / event_count if event_count > 0 else 0.0,
            "auto_threads_created": len(self._auto_thread_times.get(watcher_id, [])),
        }


class AutoDeliberationCheck:
    """Result of an auto-deliberation eligibility check."""

    def __init__(
        self,
        allowed: bool,
        watcher_id: UUID,
        event_count: int,
        useful_rate: float,
        recent_auto_threads: int,
        reasons: List[str],
    ):
        self.allowed = allowed
        self.watcher_id = watcher_id
        self.event_count = event_count
        self.useful_rate = useful_rate
        self.recent_auto_threads = recent_auto_threads
        self.reasons = reasons

    def __bool__(self) -> bool:
        return self.allowed

    @property
    def reason(self) -> str:
        """Human-readable denial reason (empty if allowed)."""
        if self.allowed:
            return "All criteria met"
        return "; ".join(self.reasons)
