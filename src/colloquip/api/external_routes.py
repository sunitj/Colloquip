"""External API for programmatic hypothesis submission and result polling.

Allows external systems to submit hypotheses for deliberation and
poll for results without using the web interface.
"""

import logging
from typing import Dict, Optional
from uuid import UUID

from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/external")


# --- Schemas ---


class SubmitHypothesisRequest(BaseModel):
    hypothesis: str = Field(min_length=5, max_length=2000)
    mode: str = "mock"
    max_turns: int = Field(default=30, ge=5, le=100)


class SubmitHypothesisResponse(BaseModel):
    thread_id: str
    hypothesis: str
    status: str


class ThreadResultResponse(BaseModel):
    thread_id: str
    hypothesis: str
    status: str
    phase: str
    post_count: int
    consensus: Optional[Dict] = None


# --- API key validation ---


def _validate_api_key(api_key: Optional[str]) -> None:
    """Validate the API key. For now, any non-empty key is accepted."""
    if not api_key:
        raise HTTPException(
            status_code=401,
            detail="API key required. Pass via X-API-Key header.",
        )


# --- Endpoints ---


@router.post("/submit")
async def submit_hypothesis(
    request: Request,
    body: SubmitHypothesisRequest,
    x_api_key: Optional[str] = Header(None),
) -> SubmitHypothesisResponse:
    """Submit a hypothesis for deliberation.

    Requires an API key via X-API-Key header.
    """
    _validate_api_key(x_api_key)

    session_manager = getattr(request.app.state, "session_manager", None)
    if session_manager is None:
        raise HTTPException(status_code=503, detail="Session manager not initialized")

    session = session_manager.create_session(
        hypothesis=body.hypothesis,
        mode=body.mode,
        max_turns=body.max_turns,
    )

    return SubmitHypothesisResponse(
        thread_id=str(session.id),
        hypothesis=session.hypothesis,
        status=session.status.value,
    )


@router.get("/results/{thread_id}")
async def get_results(
    request: Request,
    thread_id: str,
    x_api_key: Optional[str] = Header(None),
) -> ThreadResultResponse:
    """Poll for deliberation results.

    Requires an API key via X-API-Key header.
    """
    _validate_api_key(x_api_key)

    session_manager = getattr(request.app.state, "session_manager", None)
    if session_manager is None:
        raise HTTPException(status_code=503, detail="Session manager not initialized")

    try:
        tid = UUID(thread_id)
    except (ValueError, AttributeError):
        raise HTTPException(status_code=400, detail=f"Invalid thread_id: {thread_id!r}")

    session = session_manager.get_session(tid)
    if session is None:
        raise HTTPException(status_code=404, detail="Thread not found")

    posts = session_manager.get_posts(tid)
    events = session_manager.get_events(tid)

    # Look for consensus
    consensus = None
    for event in events:
        if event.get("type") == "session_complete":
            consensus = event.get("data")

    return ThreadResultResponse(
        thread_id=str(session.id),
        hypothesis=session.hypothesis,
        status=session.status.value,
        phase=session.phase.value,
        post_count=len(posts),
        consensus=consensus,
    )
