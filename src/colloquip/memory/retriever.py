"""Memory retriever: finds relevant past deliberations for new threads.

Retrieves both arena-scoped (same subreddit) and global (cross-subreddit)
memories, formatting them for injection into agent prompts.
"""

from typing import Dict, List
from uuid import UUID

from pydantic import BaseModel, Field

from colloquip.embeddings.interface import EmbeddingProvider
from colloquip.memory.store import MemoryStore, SynthesisMemory


class RetrievedMemories(BaseModel):
    """Container for memories retrieved for a new deliberation."""

    arena: List[SynthesisMemory] = Field(default_factory=list)
    global_results: List[SynthesisMemory] = Field(default_factory=list)
    # Memory ID -> list of annotation dicts
    annotations: Dict[str, List[dict]] = Field(default_factory=dict)

    def format_for_prompt(self) -> str:
        """Format retrieved memories for injection into agent prompt."""
        sections: List[str] = []

        if self.arena:
            sections.append("## Relevant Past Deliberations (This Subreddit)")
            for mem in self.arena:
                sections.append(
                    f"### {mem.topic} ({mem.created_at.strftime('%Y-%m-%d')})"
                )
                if mem.confidence_level:
                    sections.append(f"Confidence: {mem.confidence_level}")
                sections.append("Key conclusions:")
                for c in mem.key_conclusions:
                    sections.append(f"- {c}")
                # Include annotations
                mem_anns = self.annotations.get(str(mem.id), [])
                for ann in mem_anns:
                    ann_type = ann.get("annotation_type", "")
                    ann_content = ann.get("content", "")
                    if ann_type == "outdated":
                        sections.append(
                            f"**[WARNING - OUTDATED]**: {ann_content}"
                        )
                    elif ann_type == "correction":
                        sections.append(
                            f"**[Human correction]**: {ann_content}"
                        )
                    elif ann_type == "context":
                        sections.append(
                            f"**[Additional context]**: {ann_content}"
                        )
                sections.append("")

        if self.global_results:
            sections.append("## Related Deliberations (Other Subreddits)")
            for mem in self.global_results:
                sections.append(
                    f"### [{mem.subreddit_name}] {mem.topic} "
                    f"({mem.created_at.strftime('%Y-%m-%d')})"
                )
                sections.append("Key conclusions:")
                for c in mem.key_conclusions:
                    sections.append(f"- {c}")
                mem_anns = self.annotations.get(str(mem.id), [])
                for ann in mem_anns:
                    ann_type = ann.get("annotation_type", "")
                    ann_content = ann.get("content", "")
                    if ann_type == "outdated":
                        sections.append(
                            f"**[WARNING - OUTDATED]**: {ann_content}"
                        )
                    elif ann_type == "correction":
                        sections.append(
                            f"**[Human correction]**: {ann_content}"
                        )
                    elif ann_type == "context":
                        sections.append(
                            f"**[Additional context]**: {ann_content}"
                        )
                sections.append("")

        if not sections:
            return "## Prior Deliberations\nNo relevant past deliberations found."

        return "\n".join(sections)


class MemoryRetriever:
    """Retrieve relevant past deliberations for a new thread.

    Uses embedding similarity to find past syntheses that are relevant
    to the current topic. Retrieves both arena-scoped (same subreddit)
    and global (cross-subreddit) results.
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

        arena_memories = [r.memory for r in arena_results]
        global_memories = [r.memory for r in global_results]

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
        )
