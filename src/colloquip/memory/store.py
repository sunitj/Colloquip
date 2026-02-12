"""Memory store for synthesis-level institutional memory.

Phase 3a: Store full syntheses as memory documents, searchable via
vector similarity. This is the simplest useful memory system — typed
memory decomposition (Phase 3b) comes later after calibration data exists.
"""

import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from colloquip.embeddings.interface import cosine_similarity

logger = logging.getLogger(__name__)


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
    confidence_level: str = ""
    evidence_quality: str = ""

    # Embedding for similarity search
    embedding: List[float] = Field(default_factory=list)

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class MemorySearchResult(BaseModel):
    """A memory with its similarity score."""

    memory: SynthesisMemory
    similarity: float


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


class InMemoryStore(MemoryStore):
    """In-memory implementation using brute-force cosine similarity.

    Suitable for development and testing. For production, use PgVectorMemoryStore.
    """

    def __init__(self) -> None:
        self._memories: List[SynthesisMemory] = []
        self._by_id: Dict[UUID, SynthesisMemory] = {}
        self._annotations: Dict[UUID, List[Dict]] = {}

    async def save(self, memory: SynthesisMemory) -> None:
        if memory.id in self._by_id:
            # Update existing
            self._memories = [m for m in self._memories if m.id != memory.id]
        self._memories.append(memory)
        self._by_id[memory.id] = memory

    async def search(
        self,
        embedding: List[float],
        subreddit_id: UUID,
        limit: int = 3,
    ) -> List[MemorySearchResult]:
        results = []
        for memory in self._memories:
            if memory.subreddit_id != subreddit_id:
                continue
            if not memory.embedding:
                logger.debug("Skipping memory %s: no embedding", memory.id)
                continue
            sim = cosine_similarity(embedding, memory.embedding)
            results.append(MemorySearchResult(memory=memory, similarity=sim))

        results.sort(key=lambda r: r.similarity, reverse=True)
        return results[:limit]

    async def search_global(
        self,
        embedding: List[float],
        exclude_subreddit: UUID,
        limit: int = 2,
    ) -> List[MemorySearchResult]:
        results = []
        for memory in self._memories:
            if memory.subreddit_id == exclude_subreddit:
                continue
            if not memory.embedding:
                logger.debug("Skipping memory %s: no embedding", memory.id)
                continue
            sim = cosine_similarity(embedding, memory.embedding)
            results.append(MemorySearchResult(memory=memory, similarity=sim))

        results.sort(key=lambda r: r.similarity, reverse=True)
        return results[:limit]

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
        self._annotations.setdefault(memory_id, []).append({
            "id": ann_id,
            "annotation_type": annotation_type,
            "content": content,
            "created_by": created_by,
            "created_at": datetime.now(timezone.utc),
        })

    async def get_annotations(self, memory_id: UUID) -> List[Dict]:
        return self._annotations.get(memory_id, [])
