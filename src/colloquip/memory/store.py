"""Memory store for synthesis-level institutional memory.

Phase 3a: Store full syntheses as memory documents, searchable via
vector similarity. This is the simplest useful memory system — typed
memory decomposition (Phase 3b) comes later after calibration data exists.

Confidence model: Each memory carries Beta distribution parameters
(alpha, beta) representing belief in its correctness. Posterior mean
alpha/(alpha+beta) is used alongside cosine similarity and temporal
decay to produce composite retrieval scores.
"""

import logging
import math
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from colloquip.embeddings.interface import cosine_similarity

logger = logging.getLogger(__name__)

# --- Confidence constants ---

# Floor/ceiling to prevent runaway certainty or total dismissal
CONFIDENCE_FLOOR = 0.1
CONFIDENCE_CEILING = 0.95

# Default half-life for temporal decay (days)
DEFAULT_DECAY_HALF_LIFE_DAYS = 120.0

# Bayesian update increments for annotation types
ANNOTATION_UPDATES: Dict[str, tuple] = {
    # (delta_alpha, delta_beta)
    "confirmed": (2.0, 0.0),  # Strong positive from human
    "correction": (0.0, 3.0),  # Strong negative — the memory was wrong
    "outdated": (0.0, 2.0),  # Weaker negative — stale, not wrong
    "context": (0.0, 0.0),  # No confidence change, just adds nuance
}

# Bayesian update increments for outcome types
OUTCOME_UPDATES: Dict[str, tuple] = {
    # (delta_alpha, delta_beta)
    "confirmed": (1.0, 0.0),
    "partially_confirmed": (0.5, 0.5),
    "contradicted": (0.0, 2.0),  # Asymmetric: contradictions hurt more
    "inconclusive": (0.0, 0.0),
}

# Initial priors keyed by confidence_level string from synthesis metadata
INITIAL_PRIORS: Dict[str, tuple] = {
    "high": (3.0, 1.0),  # ~0.75
    "moderate": (2.0, 1.5),  # ~0.57
    "low": (1.0, 2.0),  # ~0.33
}
DEFAULT_PRIOR = (2.0, 1.0)  # ~0.67 — optimistic default


def compute_confidence(alpha: float, beta: float) -> float:
    """Posterior mean of the Beta distribution, clamped to [FLOOR, CEILING]."""
    total = alpha + beta
    if total == 0:
        return 0.5
    raw = alpha / total
    return max(CONFIDENCE_FLOOR, min(CONFIDENCE_CEILING, raw))


def temporal_decay(
    created_at: datetime,
    now: Optional[datetime] = None,
    half_life_days: float = DEFAULT_DECAY_HALF_LIFE_DAYS,
) -> float:
    """Exponential decay factor based on memory age.

    Returns a value in (0, 1] where 1.0 means brand-new and
    0.5 means the memory is exactly one half-life old.
    """
    now = now or datetime.now(timezone.utc)
    age_seconds = max(0.0, (now - created_at).total_seconds())
    age_days = age_seconds / 86400.0
    if half_life_days <= 0:
        return 1.0
    lam = math.log(2) / half_life_days
    return math.exp(-lam * age_days)


def composite_score(
    similarity: float,
    alpha: float,
    beta: float,
    created_at: datetime,
    now: Optional[datetime] = None,
    half_life_days: float = DEFAULT_DECAY_HALF_LIFE_DAYS,
) -> float:
    """Combine similarity, confidence, and recency into a single retrieval score."""
    conf = compute_confidence(alpha, beta)
    decay = temporal_decay(created_at, now=now, half_life_days=half_life_days)
    return similarity * conf * decay


class SynthesisMemory(BaseModel):
    """A stored synthesis available for retrieval in future deliberations.

    This is the Phase 3 memory unit. It's the full synthesis, not decomposed
    into typed memories. Decomposition comes in Phase 3b after we have data
    to calibrate extraction quality.
    """

    id: UUID = Field(default_factory=uuid4)
    thread_id: UUID
    subreddit_id: UUID
    subreddit_name: str

    # Content
    topic: str
    synthesis_content: str
    key_conclusions: List[str] = Field(default_factory=list)
    citations_used: List[str] = Field(default_factory=list)

    # Metadata for filtering
    agents_involved: List[str] = Field(default_factory=list)
    template_type: str = ""
    confidence_level: str = ""  # Legacy string label, kept for display
    evidence_quality: str = ""

    # Bayesian confidence (Beta distribution parameters)
    # Posterior mean = alpha / (alpha + beta)
    # Initialized from synthesis metadata; updated by outcomes and annotations.
    confidence_alpha: float = Field(default=2.0, ge=0.0)
    confidence_beta: float = Field(default=1.0, ge=0.0)

    # Embedding for similarity search
    embedding: List[float] = Field(default_factory=list)

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def confidence(self) -> float:
        """Posterior mean of the Beta distribution, clamped."""
        return compute_confidence(self.confidence_alpha, self.confidence_beta)


class MemorySearchResult(BaseModel):
    """A memory with its similarity and composite scores."""

    memory: SynthesisMemory
    similarity: float
    score: float = 0.0  # composite_score (similarity * confidence * decay)


class RetrievalLogEntry(BaseModel):
    """Record of a single memory retrieval event for observability."""

    id: UUID = Field(default_factory=uuid4)
    query_topic: str
    subreddit_id: UUID
    memory_id: UUID
    similarity: float
    confidence: float
    decay_factor: float
    composite_score: float
    scope: str  # "arena" or "global"
    retrieved_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class MemoryStore(ABC):
    """Abstract base for synthesis memory storage and retrieval."""

    @abstractmethod
    async def save(self, memory: SynthesisMemory) -> None:
        """Store a synthesis memory."""
        ...

    @abstractmethod
    async def search(
        self,
        embedding: List[float],
        subreddit_id: UUID,
        limit: int = 3,
    ) -> List[MemorySearchResult]:
        """Search for similar memories within a specific subreddit."""
        ...

    @abstractmethod
    async def search_global(
        self,
        embedding: List[float],
        exclude_subreddit: UUID,
        limit: int = 2,
    ) -> List[MemorySearchResult]:
        """Search for similar memories across all subreddits except the given one."""
        ...

    @abstractmethod
    async def get(self, memory_id: UUID) -> Optional[SynthesisMemory]:
        """Retrieve a specific memory by ID."""
        ...

    @abstractmethod
    async def list_all(self, limit: int = 50) -> List[SynthesisMemory]:
        """List all memories, ordered by creation date (newest first)."""
        ...

    @abstractmethod
    async def list_by_subreddit(self, subreddit_id: UUID) -> List[SynthesisMemory]:
        """List all memories for a subreddit, ordered by creation date."""
        ...

    @abstractmethod
    async def count(self) -> int:
        """Total number of stored memories."""
        ...

    @abstractmethod
    async def annotate(
        self,
        memory_id: UUID,
        annotation_type: str,
        content: str,
        created_by: Optional[str] = None,
    ) -> None:
        """Add an annotation to a memory.

        Raises ValueError if the memory does not exist.
        """
        ...

    @abstractmethod
    async def get_annotations(self, memory_id: UUID) -> List[Dict]:
        """Get all annotations for a memory."""
        ...

    async def update_confidence(
        self,
        memory_id: UUID,
        delta_alpha: float = 0.0,
        delta_beta: float = 0.0,
    ) -> Optional[SynthesisMemory]:
        """Apply a Bayesian update to a memory's confidence parameters.

        Returns the updated memory, or None if the memory doesn't exist.
        Default implementation works for any store that implements get() and save().
        """
        memory = await self.get(memory_id)
        if memory is None:
            return None
        memory.confidence_alpha = max(0.0, memory.confidence_alpha + delta_alpha)
        memory.confidence_beta = max(0.0, memory.confidence_beta + delta_beta)
        await self.save(memory)
        logger.info(
            "Updated confidence for memory %s: alpha=%.2f, beta=%.2f (confidence=%.2f)",
            memory_id,
            memory.confidence_alpha,
            memory.confidence_beta,
            memory.confidence,
        )
        return memory


class InMemoryStore(MemoryStore):
    """In-memory implementation using brute-force cosine similarity.

    Suitable for development and testing. For production, use PgVectorMemoryStore.
    """

    def __init__(self, decay_half_life_days: float = DEFAULT_DECAY_HALF_LIFE_DAYS) -> None:
        self._memories: List[SynthesisMemory] = []
        self._by_id: Dict[UUID, SynthesisMemory] = {}
        self._annotations: Dict[UUID, List[Dict]] = {}
        self._retrieval_log: List[RetrievalLogEntry] = []
        self.decay_half_life_days = decay_half_life_days

    async def save(self, memory: SynthesisMemory) -> None:
        if memory.id in self._by_id:
            # Update existing
            self._memories = [m for m in self._memories if m.id != memory.id]
        self._memories.append(memory)
        self._by_id[memory.id] = memory

    def _score_memories(
        self, embedding: List[float], candidates: List[SynthesisMemory]
    ) -> List[MemorySearchResult]:
        """Score a list of candidate memories using composite scoring."""
        now = datetime.now(timezone.utc)
        results = []
        for memory in candidates:
            if not memory.embedding:
                logger.debug("Skipping memory %s: no embedding", memory.id)
                continue
            sim = cosine_similarity(embedding, memory.embedding)
            score = composite_score(
                similarity=sim,
                alpha=memory.confidence_alpha,
                beta=memory.confidence_beta,
                created_at=memory.created_at,
                now=now,
                half_life_days=self.decay_half_life_days,
            )
            results.append(MemorySearchResult(memory=memory, similarity=sim, score=score))
        results.sort(key=lambda r: r.score, reverse=True)
        return results

    async def search(
        self,
        embedding: List[float],
        subreddit_id: UUID,
        limit: int = 3,
    ) -> List[MemorySearchResult]:
        candidates = [m for m in self._memories if m.subreddit_id == subreddit_id]
        return self._score_memories(embedding, candidates)[:limit]

    async def search_global(
        self,
        embedding: List[float],
        exclude_subreddit: UUID,
        limit: int = 2,
    ) -> List[MemorySearchResult]:
        candidates = [m for m in self._memories if m.subreddit_id != exclude_subreddit]
        return self._score_memories(embedding, candidates)[:limit]

    async def get(self, memory_id: UUID) -> Optional[SynthesisMemory]:
        return self._by_id.get(memory_id)

    async def list_all(self, limit: int = 50) -> List[SynthesisMemory]:
        return sorted(
            self._memories,
            key=lambda m: m.created_at,
            reverse=True,
        )[:limit]

    async def list_by_subreddit(self, subreddit_id: UUID) -> List[SynthesisMemory]:
        return sorted(
            [m for m in self._memories if m.subreddit_id == subreddit_id],
            key=lambda m: m.created_at,
            reverse=True,
        )

    async def count(self) -> int:
        return len(self._memories)

    async def annotate(
        self,
        memory_id: UUID,
        annotation_type: str,
        content: str,
        created_by: Optional[str] = None,
    ) -> None:
        if memory_id not in self._by_id:
            raise ValueError(f"Memory {memory_id} not found")
        ann_id = str(uuid4())
        self._annotations.setdefault(memory_id, []).append(
            {
                "id": ann_id,
                "annotation_type": annotation_type,
                "content": content,
                "created_by": created_by,
                "created_at": datetime.now(timezone.utc),
            }
        )

        # Apply Bayesian update from annotation type
        deltas = ANNOTATION_UPDATES.get(annotation_type, (0.0, 0.0))
        if deltas[0] != 0.0 or deltas[1] != 0.0:
            await self.update_confidence(memory_id, delta_alpha=deltas[0], delta_beta=deltas[1])

    async def get_annotations(self, memory_id: UUID) -> List[Dict]:
        return self._annotations.get(memory_id, [])

    # --- Retrieval logging ---

    def log_retrieval(self, entry: RetrievalLogEntry) -> None:
        """Record a retrieval event for observability."""
        self._retrieval_log.append(entry)

    def get_retrieval_log(self, limit: int = 100) -> List[RetrievalLogEntry]:
        """Return recent retrieval log entries (newest first)."""
        return sorted(self._retrieval_log, key=lambda e: e.retrieved_at, reverse=True)[:limit]
