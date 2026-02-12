"""Triage agent for evaluating watcher events.

Evaluates events on NOVELTY, RELEVANCE, SIGNAL, and URGENCY dimensions
and produces a TriageDecision with a signal level (low/medium/high).

The mock implementation uses simple heuristics for testing.
The LLM implementation (future) will use a single LLM call with <500 tokens.
"""

import logging
from abc import ABC, abstractmethod
from typing import List, Optional

from colloquip.models import (
    TriageDecision,
    TriageSignal,
    WatcherConfig,
    WatcherEvent,
)

logger = logging.getLogger(__name__)


class TriageAgent(ABC):
    """Abstract triage agent that evaluates watcher events."""

    @abstractmethod
    async def evaluate(
        self,
        event: WatcherEvent,
        watcher_config: WatcherConfig,
        recent_events: Optional[List[WatcherEvent]] = None,
    ) -> TriageDecision:
        """Evaluate an event and produce a triage decision.

        Args:
            event: The event to evaluate
            watcher_config: Config of the watcher that produced this event
            recent_events: Recent events from the same watcher (for dedup)

        Returns:
            TriageDecision with signal level and reasoning
        """
        ...


class MockTriageAgent(TriageAgent):
    """Mock triage agent using keyword heuristics.

    Scores based on:
    - Title/summary length (proxy for information density)
    - Keyword matching against watcher query
    - Deduplication against recent events
    """

    def __init__(
        self,
        high_threshold: float = 0.7,
        medium_threshold: float = 0.4,
    ):
        self.high_threshold = high_threshold
        self.medium_threshold = medium_threshold

    async def evaluate(
        self,
        event: WatcherEvent,
        watcher_config: WatcherConfig,
        recent_events: Optional[List[WatcherEvent]] = None,
    ) -> TriageDecision:
        """Evaluate using keyword heuristics."""
        recent = recent_events or []

        # Check for duplicates
        if self._is_duplicate(event, recent):
            return TriageDecision(
                event_id=event.id,
                signal=TriageSignal.LOW,
                novelty=0.0,
                relevance=0.0,
                urgency=0.0,
                reasoning="Duplicate of recent event",
            )

        # Score dimensions
        novelty = self._score_novelty(event, recent)
        relevance = self._score_relevance(event, watcher_config)
        urgency = self._score_urgency(event)

        # Composite score
        composite = 0.4 * novelty + 0.4 * relevance + 0.2 * urgency

        # Determine signal level
        if composite >= self.high_threshold:
            signal = TriageSignal.HIGH
        elif composite >= self.medium_threshold:
            signal = TriageSignal.MEDIUM
        else:
            signal = TriageSignal.LOW

        # Generate suggested hypothesis for high-signal events
        hypothesis = None
        if signal in (TriageSignal.HIGH, TriageSignal.MEDIUM):
            hypothesis = self._suggest_hypothesis(event, watcher_config)

        return TriageDecision(
            event_id=event.id,
            signal=signal,
            novelty=novelty,
            relevance=relevance,
            urgency=urgency,
            reasoning=self._build_reasoning(novelty, relevance, urgency, composite),
            suggested_hypothesis=hypothesis,
        )

    def _is_duplicate(
        self, event: WatcherEvent, recent: List[WatcherEvent]
    ) -> bool:
        """Check if event is a duplicate of a recent event."""
        for prev in recent:
            if (
                event.source.source_id
                and event.source.source_id == prev.source.source_id
            ):
                return True
            if event.title == prev.title and event.summary == prev.summary:
                return True
        return False

    def _score_novelty(
        self, event: WatcherEvent, recent: List[WatcherEvent]
    ) -> float:
        """Score novelty based on title uniqueness vs recent events."""
        if not recent:
            return 0.8  # First event is novel by default

        event_words = set(event.title.lower().split())
        max_overlap = 0.0
        for prev in recent:
            prev_words = set(prev.title.lower().split())
            if event_words and prev_words:
                overlap = len(event_words & prev_words) / max(
                    len(event_words), len(prev_words)
                )
                max_overlap = max(max_overlap, overlap)

        # Less overlap = more novel
        return max(0.0, min(1.0, 1.0 - max_overlap))

    def _score_relevance(
        self, event: WatcherEvent, config: WatcherConfig
    ) -> float:
        """Score relevance based on keyword overlap with watcher query."""
        if not config.query:
            return 0.5  # Default relevance if no query

        query_words = set(config.query.lower().split())
        text = f"{event.title} {event.summary}".lower()
        text_words = set(text.split())

        if not query_words:
            return 0.5

        matches = len(query_words & text_words)
        return min(1.0, matches / max(1, len(query_words)))

    def _score_urgency(self, event: WatcherEvent) -> float:
        """Score urgency based on event metadata."""
        # Check for urgency hints in raw_data
        urgency_keywords = {"breakthrough", "urgent", "critical", "novel", "first"}
        text = f"{event.title} {event.summary}".lower()
        matches = sum(1 for kw in urgency_keywords if kw in text)
        return min(1.0, matches * 0.3)

    def _suggest_hypothesis(
        self, event: WatcherEvent, config: WatcherConfig
    ) -> str:
        """Generate a suggested deliberation hypothesis from the event."""
        return (
            f"Evaluate the implications of: {event.title}. "
            f"Context: {event.summary[:200]}"
        )

    def _build_reasoning(
        self,
        novelty: float,
        relevance: float,
        urgency: float,
        composite: float,
    ) -> str:
        """Build human-readable reasoning string."""
        parts = []
        if novelty >= 0.7:
            parts.append("highly novel")
        elif novelty >= 0.4:
            parts.append("moderately novel")
        else:
            parts.append("low novelty")

        if relevance >= 0.7:
            parts.append("highly relevant")
        elif relevance >= 0.4:
            parts.append("moderately relevant")
        else:
            parts.append("low relevance")

        if urgency >= 0.5:
            parts.append("urgent indicators present")

        return f"Composite score {composite:.2f}: {', '.join(parts)}"
