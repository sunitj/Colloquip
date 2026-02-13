"""Outcome tracking: record real-world results of deliberation conclusions.

Allows humans to report whether deliberation conclusions were confirmed,
contradicted, or partially validated by subsequent real-world evidence.
"""

import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class OutcomeType:
    CONFIRMED = "confirmed"
    PARTIALLY_CONFIRMED = "partially_confirmed"
    CONTRADICTED = "contradicted"
    INCONCLUSIVE = "inconclusive"


class OutcomeReport(BaseModel):
    """A report on the real-world outcome of a deliberation."""

    id: UUID = Field(default_factory=uuid4)
    thread_id: UUID
    subreddit_id: UUID
    outcome_type: str  # confirmed, partially_confirmed, contradicted, inconclusive
    summary: str
    evidence: str = ""
    conclusions_evaluated: List[str] = Field(default_factory=list)
    agent_assessments: Dict[str, str] = Field(default_factory=dict)
    # Maps agent_id -> "correct" | "incorrect" | "partial" | "not_evaluated"
    reported_by: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class OutcomeTracker(ABC):
    """Abstract base for outcome storage and retrieval."""

    @abstractmethod
    async def save_outcome(self, outcome: OutcomeReport) -> None:
        """Save an outcome report."""
        ...

    @abstractmethod
    async def get_outcome(self, outcome_id: UUID) -> Optional[OutcomeReport]:
        """Get an outcome by ID."""
        ...

    @abstractmethod
    async def get_outcomes_for_thread(self, thread_id: UUID) -> List[OutcomeReport]:
        """Get all outcomes for a deliberation thread."""
        ...

    @abstractmethod
    async def get_outcomes_for_subreddit(self, subreddit_id: UUID) -> List[OutcomeReport]:
        """Get all outcomes for a subreddit."""
        ...

    @abstractmethod
    async def list_all(self, limit: int = 50) -> List[OutcomeReport]:
        """List all outcomes, newest first."""
        ...


class InMemoryOutcomeTracker(OutcomeTracker):
    """In-memory outcome tracker for development and testing."""

    def __init__(self) -> None:
        self._outcomes: List[OutcomeReport] = []
        self._by_id: Dict[UUID, OutcomeReport] = {}

    async def save_outcome(self, outcome: OutcomeReport) -> None:
        if outcome.id in self._by_id:
            self._outcomes = [o for o in self._outcomes if o.id != outcome.id]
        self._outcomes.append(outcome)
        self._by_id[outcome.id] = outcome

    async def get_outcome(self, outcome_id: UUID) -> Optional[OutcomeReport]:
        return self._by_id.get(outcome_id)

    async def get_outcomes_for_thread(self, thread_id: UUID) -> List[OutcomeReport]:
        return sorted(
            [o for o in self._outcomes if o.thread_id == thread_id],
            key=lambda o: o.created_at,
            reverse=True,
        )

    async def get_outcomes_for_subreddit(self, subreddit_id: UUID) -> List[OutcomeReport]:
        return sorted(
            [o for o in self._outcomes if o.subreddit_id == subreddit_id],
            key=lambda o: o.created_at,
            reverse=True,
        )

    async def list_all(self, limit: int = 50) -> List[OutcomeReport]:
        return sorted(
            self._outcomes,
            key=lambda o: o.created_at,
            reverse=True,
        )[:limit]
