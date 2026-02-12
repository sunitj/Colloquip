"""Event-driven watcher system for monitoring external sources.

Phase 4: Watchers detect events (new papers, scheduled triggers, webhooks),
triage them for relevance, and generate notifications for human review.
"""

from colloquip.watchers.interface import BaseWatcher, WatcherRegistry
from colloquip.watchers.triage import MockTriageAgent, TriageAgent

__all__ = [
    "BaseWatcher",
    "WatcherRegistry",
    "TriageAgent",
    "MockTriageAgent",
]
