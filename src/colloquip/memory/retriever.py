"""Memory retriever: finds relevant past deliberations for new threads.

Retrieves both arena-scoped (same subreddit) and global (cross-subreddit)
memories, formatting them for injection into agent prompts.

Retrieval logging: every retrieval event is recorded for observability,
enabling future analysis of memory usage patterns and decay calibration.
"""

import logging
from typing import Dict, List
from uuid import UUID

from pydantic import BaseModel, Field

from colloquip.embeddings.interface import EmbeddingProvider
from colloquip.memory.store import (
    MemorySearchResult,
    MemoryStore,
    RetrievalLogEntry,
    SynthesisMemory,
    temporal_decay,
)

logger = logging.getLogger(__name__)


class RetrievedMemories(BaseModel):
    """Container for memories retrieved for a new deliberation."""

    arena: List[SynthesisMemory] = Field(default_factory=list)
    global_results: List[SynthesisMemory] = Field(default_factory=list)
    # Memory ID -> list of annotation dicts
    annotations: Dict[str, List[dict]] = Field(default_factory=dict)
    # Memory ID -> composite score from retrieval
    scores: Dict[str, float] = Field(default_factory=dict)

    def format_for_prompt(self) -> str:
        """Format retrieved memories for injection into agent prompt."""
        sections: List[str] = []

        if self.arena:
            sections.append("## Relevant Past Deliberations (This Subreddit)")
            for mem in self.arena:
                sections.append(f"### {mem.topic} ({mem.created_at.strftime('%Y-%m-%d')})")
                sections.append(f"Confidence: {mem.confidence:.0%}")
                sections.append("Key conclusions:")
                for c in mem.key_conclusions:
                    sections.append(f"- {c}")
                self._format_annotations(sections, mem)
                sections.append("")

        if self.global_results:
            sections.append("## Related Deliberations (Other Subreddits)")
            for mem in self.global_results:
                sections.append(
                    f"### [{mem.subreddit_name}] {mem.topic} "
                    f"({mem.created_at.strftime('%Y-%m-%d')})"
                )
                sections.append(f"Confidence: {mem.confidence:.0%}")
                sections.append("Key conclusions:")
                for c in mem.key_conclusions:
                    sections.append(f"- {c}")
                self._format_annotations(sections, mem)
                sections.append("")

        if not sections:
            return "## Prior Deliberations\nNo relevant past deliberations found."

        return "\n".join(sections)

    def _format_annotations(self, sections: List[str], mem: SynthesisMemory) -> None:
        """Append annotation lines for a memory (shared logic)."""
        mem_anns = self.annotations.get(str(mem.id), [])
        for ann in mem_anns:
            ann_type = ann.get("annotation_type", "")
            ann_content = ann.get("content", "")
            if ann_type == "outdated":
                sections.append(f"**[WARNING - OUTDATED]**: {ann_content}")
            elif ann_type == "correction":
                sections.append(f"**[Human correction]**: {ann_content}")
            elif ann_type == "context":
                sections.append(f"**[Additional context]**: {ann_content}")


class MemoryRetriever:
    """Retrieve relevant past deliberations for a new thread.

    Uses composite scoring (similarity * confidence * decay) to find
    past syntheses relevant to the current topic. Records every retrieval
    for observability and future decay calibration.
    """

    def __init__(
        self,
        store: MemoryStore,
        embedding_provider: EmbeddingProvider,
    ):
        self.store = store
        self.embedding_provider = embedding_provider

    async def retrieve(
        self,
        topic: str,
        subreddit_id: UUID,
        max_arena: int = 3,
        max_global: int = 2,
    ) -> RetrievedMemories:
        """Retrieve relevant past syntheses with their annotations."""
        topic_embedding = await self.embedding_provider.embed(topic)

        arena_results = await self.store.search(
            embedding=topic_embedding,
            subreddit_id=subreddit_id,
            limit=max_arena,
        )

        global_results = await self.store.search_global(
            embedding=topic_embedding,
            exclude_subreddit=subreddit_id,
            limit=max_global,
        )

        # Log retrieval events
        self._log_results(arena_results, topic, subreddit_id, scope="arena")
        self._log_results(global_results, topic, subreddit_id, scope="global")

        arena_memories = [r.memory for r in arena_results]
        global_memories = [r.memory for r in global_results]

        # Build scores map
        scores: Dict[str, float] = {}
        for r in arena_results + global_results:
            scores[str(r.memory.id)] = r.score

        # Fetch annotations for all retrieved memories
        all_memories = arena_memories + global_memories
        annotations: Dict[str, List[dict]] = {}
        for mem in all_memories:
            anns = await self.store.get_annotations(mem.id)
            if anns:
                annotations[str(mem.id)] = anns

        return RetrievedMemories(
            arena=arena_memories,
            global_results=global_memories,
            annotations=annotations,
            scores=scores,
        )

    def _log_results(
        self,
        results: List[MemorySearchResult],
        topic: str,
        subreddit_id: UUID,
        scope: str,
    ) -> None:
        """Record retrieval events to the store's log."""
        if not hasattr(self.store, "log_retrieval"):
            return
        for r in results:
            decay = temporal_decay(r.memory.created_at)
            entry = RetrievalLogEntry(
                query_topic=topic,
                subreddit_id=subreddit_id,
                memory_id=r.memory.id,
                similarity=r.similarity,
                confidence=r.memory.confidence,
                decay_factor=decay,
                composite_score=r.score,
                scope=scope,
            )
            self.store.log_retrieval(entry)
