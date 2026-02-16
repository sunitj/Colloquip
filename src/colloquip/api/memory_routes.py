"""API routes for institutional memory management.

Endpoints for listing, viewing, and annotating synthesis memories.
"""

import logging
from typing import List, Literal, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from colloquip.api.utils import parse_uuid as _parse_uuid
from colloquip.memory.store import MemoryStore

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")


# --- Helpers ---


def _get_store(request: Request) -> MemoryStore:
    """Get the memory store from app state, raising 503 if not initialized."""
    store = getattr(request.app.state, "memory_store", None)
    if store is None:
        raise HTTPException(status_code=503, detail="Memory system not initialized")
    return store


# --- Request / Response schemas ---


class AnnotateMemoryRequest(BaseModel):
    annotation_type: Literal["outdated", "correction", "confirmed", "context"]
    content: str = Field(min_length=1, max_length=5000)
    created_by: Optional[str] = None


class AnnotationResponse(BaseModel):
    id: str
    memory_id: str
    annotation_type: str
    content: str
    created_by: Optional[str]
    created_at: str


class MemoryResponse(BaseModel):
    id: str
    thread_id: str
    subreddit_id: str
    subreddit_name: str
    topic: str
    key_conclusions: List[str]
    citations_used: List[str]
    agents_involved: List[str]
    template_type: str
    confidence_level: str
    evidence_quality: str
    confidence: float  # Bayesian posterior mean
    confidence_alpha: float
    confidence_beta: float
    created_at: str
    annotations: List[AnnotationResponse] = Field(default_factory=list)


class MemoryListResponse(BaseModel):
    memories: List[MemoryResponse]
    total: int


# --- Endpoints ---


@router.get("/memories")
async def list_memories(
    request: Request,
    subreddit_id: Optional[str] = None,
    limit: int = 50,
) -> MemoryListResponse:
    """List synthesis memories, optionally filtered by subreddit."""
    store = _get_store(request)

    if subreddit_id:
        sub_uuid = _parse_uuid(subreddit_id, "subreddit_id")
        memories = await store.list_by_subreddit(sub_uuid)
        memories = memories[:limit]
    else:
        memories = await store.list_all(limit=limit)

    result_memories = []
    for mem in memories:
        annotations = await store.get_annotations(mem.id)
        result_memories.append(_format_memory(mem, annotations))

    return MemoryListResponse(memories=result_memories, total=len(result_memories))


@router.get("/memories/{memory_id}")
async def get_memory(request: Request, memory_id: str) -> MemoryResponse:
    """Get a specific memory with its annotations."""
    store = _get_store(request)
    mem_uuid = _parse_uuid(memory_id, "memory_id")

    mem = await store.get(mem_uuid)
    if not mem:
        raise HTTPException(status_code=404, detail="Memory not found")

    annotations = await store.get_annotations(mem.id)
    return _format_memory(mem, annotations)


@router.post("/memories/{memory_id}/annotate")
async def annotate_memory(
    request: Request,
    memory_id: str,
    body: AnnotateMemoryRequest,
) -> AnnotationResponse:
    """Add an annotation to a synthesis memory."""
    store = _get_store(request)
    mem_uuid = _parse_uuid(memory_id, "memory_id")

    mem = await store.get(mem_uuid)
    if not mem:
        raise HTTPException(status_code=404, detail="Memory not found")

    await store.annotate(
        memory_id=mem.id,
        annotation_type=body.annotation_type,
        content=body.content,
        created_by=body.created_by,
    )

    # Return the latest annotation
    annotations = await store.get_annotations(mem.id)
    if not annotations:
        raise HTTPException(status_code=500, detail="Failed to save annotation")
    ann = annotations[-1]
    return AnnotationResponse(
        id=ann.get("id", ""),
        memory_id=memory_id,
        annotation_type=ann["annotation_type"],
        content=ann["content"],
        created_by=ann.get("created_by"),
        created_at=str(ann.get("created_at", "")),
    )


@router.get("/subreddits/{subreddit_name}/memories")
async def get_subreddit_memories(
    request: Request,
    subreddit_name: str,
    limit: int = 50,
) -> MemoryListResponse:
    """Get memories for a specific subreddit by name."""
    store = _get_store(request)

    # Use list_all and filter by name (no ABC method for name-based lookup)
    all_memories = await store.list_all(limit=500)
    memories = [m for m in all_memories if m.subreddit_name == subreddit_name][:limit]

    result_memories = []
    for mem in memories:
        annotations = await store.get_annotations(mem.id)
        result_memories.append(_format_memory(mem, annotations))

    return MemoryListResponse(memories=result_memories, total=len(result_memories))


# --- Helpers ---


def _format_memory(mem, annotations: list) -> MemoryResponse:
    return MemoryResponse(
        id=str(mem.id),
        thread_id=str(mem.thread_id),
        subreddit_id=str(mem.subreddit_id),
        subreddit_name=mem.subreddit_name,
        topic=mem.topic,
        key_conclusions=mem.key_conclusions,
        citations_used=mem.citations_used,
        agents_involved=mem.agents_involved,
        template_type=mem.template_type,
        confidence_level=mem.confidence_level,
        evidence_quality=mem.evidence_quality,
        confidence=mem.confidence,
        confidence_alpha=mem.confidence_alpha,
        confidence_beta=mem.confidence_beta,
        created_at=str(mem.created_at),
        annotations=[
            AnnotationResponse(
                id=str(a.get("id", "")),
                memory_id=str(mem.id),
                annotation_type=a["annotation_type"],
                content=a["content"],
                created_by=a.get("created_by"),
                created_at=str(a.get("created_at", "")),
            )
            for a in annotations
        ],
    )
