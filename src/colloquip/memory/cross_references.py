"""Cross-subreddit reference detection.

Detects when findings in one subreddit are relevant to another using
three criteria (ALL must be met):
1. Embedding similarity > threshold
2. Shared entity (gene/compound/disease/citation)
3. Actionable in target context
"""

import logging
import re
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from colloquip.embeddings.interface import EmbeddingProvider, cosine_similarity
from colloquip.memory.store import MemoryStore, SynthesisMemory

logger = logging.getLogger(__name__)

# Entity extraction patterns
_PMID_PATTERN = re.compile(r"PMID[:\s]?(\d+)", re.IGNORECASE)
_GENE_PATTERN = re.compile(r"\b([A-Z][A-Z0-9]{1,6})\b")  # Simple gene name heuristic
_COMPOUND_PATTERN = re.compile(r"\b([A-Z]{2,3}-\d{3,})\b")  # e.g. GLP-1, ABC-123


class CrossReference(BaseModel):
    """A detected cross-reference between two memories in different subreddits."""

    id: UUID = Field(default_factory=uuid4)
    source_memory_id: UUID
    target_memory_id: UUID
    source_subreddit_id: UUID
    target_subreddit_id: UUID
    source_subreddit_name: str
    target_subreddit_name: str
    similarity: float = 0.0
    shared_entities: List[str] = Field(default_factory=list)
    reasoning: str = ""
    status: str = "pending"  # pending, confirmed, dismissed
    reviewed_by: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


def extract_entities(text: str) -> Set[str]:
    """Extract entities (PMIDs, gene names, compound IDs) from text."""
    entities = set()

    # PMIDs
    for match in _PMID_PATTERN.finditer(text):
        entities.add(f"PMID:{match.group(1)}")

    # Gene names (uppercase 2-7 char words)
    for match in _GENE_PATTERN.finditer(text):
        name = match.group(1)
        # Filter common English words that match the pattern
        if name not in _COMMON_WORDS and len(name) >= 2:
            entities.add(f"GENE:{name}")

    # Compound IDs
    for match in _COMPOUND_PATTERN.finditer(text):
        entities.add(f"COMPOUND:{match.group(1)}")

    return entities


# Common English words that look like gene names
_COMMON_WORDS = {
    "THE", "AND", "FOR", "ARE", "BUT", "NOT", "YOU", "ALL",
    "CAN", "HER", "WAS", "ONE", "OUR", "OUT", "DAY", "HAD",
    "HAS", "HIS", "HOW", "NEW", "NOW", "OLD", "SEE", "WAY",
    "WHO", "DID", "GET", "LET", "SAY", "SHE", "TOO", "USE",
    "KEY", "MAY", "LOW", "HIGH", "TWO", "MET", "SET", "PUT",
}


class CrossReferenceDetector:
    """Detects cross-subreddit references between synthesis memories.

    All three criteria must be met for a reference to be flagged:
    1. Embedding similarity > threshold
    2. At least one shared entity
    3. Both memories have substantive key conclusions (actionability proxy)
    """

    def __init__(
        self,
        memory_store: MemoryStore,
        embedding_provider: EmbeddingProvider,
        similarity_threshold: float = 0.75,
    ):
        self.store = memory_store
        self.embedding_provider = embedding_provider
        self.similarity_threshold = similarity_threshold

    async def detect_for_memory(
        self,
        memory: SynthesisMemory,
        exclude_subreddit: Optional[UUID] = None,
    ) -> List[CrossReference]:
        """Detect cross-references for a given memory against other subreddits."""
        exclude = exclude_subreddit or memory.subreddit_id

        if not memory.embedding:
            logger.debug("Memory %s has no embedding, skipping", memory.id)
            return []

        # Search globally for similar memories
        global_results = await self.store.search_global(
            embedding=memory.embedding,
            exclude_subreddit=exclude,
            limit=10,
        )

        # Extract entities from source memory
        source_text = f"{memory.topic} {memory.synthesis_content} {' '.join(memory.key_conclusions)}"
        source_entities = extract_entities(source_text)

        references = []
        for result in global_results:
            target = result.memory

            # Criterion 1: Similarity threshold
            if result.similarity < self.similarity_threshold:
                continue

            # Criterion 2: Shared entities
            target_text = f"{target.topic} {target.synthesis_content} {' '.join(target.key_conclusions)}"
            target_entities = extract_entities(target_text)
            shared = source_entities & target_entities
            if not shared:
                continue

            # Criterion 3: Actionability (both have key conclusions)
            if not memory.key_conclusions or not target.key_conclusions:
                continue

            ref = CrossReference(
                source_memory_id=memory.id,
                target_memory_id=target.id,
                source_subreddit_id=memory.subreddit_id,
                target_subreddit_id=target.subreddit_id,
                source_subreddit_name=memory.subreddit_name,
                target_subreddit_name=target.subreddit_name,
                similarity=result.similarity,
                shared_entities=sorted(shared),
                reasoning=self._build_reasoning(memory, target, shared, result.similarity),
            )
            references.append(ref)

        return references

    def _build_reasoning(
        self,
        source: SynthesisMemory,
        target: SynthesisMemory,
        shared_entities: Set[str],
        similarity: float,
    ) -> str:
        """Build a human-readable explanation for the cross-reference."""
        entity_str = ", ".join(sorted(shared_entities)[:5])
        return (
            f"Memory '{source.topic}' in {source.subreddit_name} is related to "
            f"'{target.topic}' in {target.subreddit_name} "
            f"(similarity: {similarity:.2f}, shared entities: {entity_str})"
        )
