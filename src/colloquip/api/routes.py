"""REST API endpoints for the Colloquip deliberation system."""

import asyncio
import json
import logging
from typing import Literal, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from colloquip.api.app import SessionManager
from colloquip.models import HumanIntervention

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")


# --- Request / Response schemas ---

class CreateSessionRequest(BaseModel):
    hypothesis: str = Field(min_length=1, max_length=2000)
    mode: Literal["mock", "real"] = "mock"
    seed: int = 42
    model: Optional[str] = None
    max_turns: int = Field(default=30, ge=1, le=100)


class CreateSessionResponse(BaseModel):
    id: str
    hypothesis: str
    status: str


class InterventionRequest(BaseModel):
    type: Literal["question", "data", "redirect", "terminate"]
    content: str = Field(min_length=1, max_length=5000)


class SessionStateResponse(BaseModel):
    id: str
    hypothesis: str
    status: str
    phase: str
    post_count: int
    energy_history: list


class EnergyHistoryResponse(BaseModel):
    session_id: str
    energy_history: list


# --- Helper to get session manager from app state ---

def _get_manager(request: Request) -> SessionManager:
    return request.app.state.session_manager


# --- Endpoints ---

@router.post("/deliberations", response_model=CreateSessionResponse)
async def create_deliberation(body: CreateSessionRequest, request: Request):
    """Create a new deliberation session."""
    manager = _get_manager(request)
    session = manager.create_session(
        hypothesis=body.hypothesis,
        mode=body.mode,
        seed=body.seed,
        model=body.model,
        max_turns=body.max_turns,
    )
    return CreateSessionResponse(
        id=str(session.id),
        hypothesis=session.hypothesis,
        status=session.status.value,
    )


@router.post("/deliberations/{session_id}/start")
async def start_deliberation(session_id: UUID, request: Request):
    """Start a deliberation and stream events via SSE."""
    manager = _get_manager(request)
    session = manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Subscribe to events before starting
    queue = manager.subscribe(session_id)

    # Start the deliberation in the background
    try:
        await manager.start_deliberation(session_id)
    except ValueError as e:
        manager.unsubscribe(session_id, queue)
        raise HTTPException(status_code=400, detail=str(e))

    async def event_stream():
        try:
            while True:
                event = await asyncio.wait_for(queue.get(), timeout=120)
                event_type = event.get("type", "message")
                data = json.dumps(event.get("data"), default=str)
                yield f"event: {event_type}\ndata: {data}\n\n"

                if event_type in ("done", "error"):
                    break
        except asyncio.TimeoutError:
            yield f"event: timeout\ndata: {{}}\n\n"
        finally:
            manager.unsubscribe(session_id, queue)
            manager.cancel_if_no_subscribers(session_id)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/deliberations/{session_id}/intervene")
async def intervene(session_id: UUID, body: InterventionRequest, request: Request):
    """Submit a human intervention to an active deliberation."""
    manager = _get_manager(request)
    session = manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    intervention = HumanIntervention(
        session_id=session_id,
        type=body.type,
        content=body.content,
    )

    try:
        result_posts = await manager.intervene(session_id, intervention)
        return {
            "posts": [p.model_dump(mode="json") for p in result_posts],
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/deliberations/{session_id}", response_model=SessionStateResponse)
async def get_session(session_id: UUID, request: Request):
    """Get the current state of a deliberation session."""
    manager = _get_manager(request)
    session = manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    posts = manager.get_posts(session_id)
    energy_history = manager.get_energy_history(session_id)

    return SessionStateResponse(
        id=str(session.id),
        hypothesis=session.hypothesis,
        status=session.status.value,
        phase=session.phase.value,
        post_count=len(posts),
        energy_history=energy_history,
    )


@router.get("/deliberations/{session_id}/energy", response_model=EnergyHistoryResponse)
async def get_energy_history(session_id: UUID, request: Request):
    """Get energy history as a time series for a session."""
    manager = _get_manager(request)
    session = manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    energy_history = manager.get_energy_history(session_id)
    return EnergyHistoryResponse(
        session_id=str(session_id),
        energy_history=energy_history,
    )


@router.get("/deliberations/{session_id}/posts")
async def get_posts(session_id: UUID, request: Request):
    """Get all posts for a deliberation session."""
    manager = _get_manager(request)
    session = manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    posts = manager.get_posts(session_id)
    return {"posts": [p.model_dump(mode="json") for p in posts]}


@router.get("/deliberations/{session_id}/events")
async def get_events(
    session_id: UUID, request: Request, since: int = 0
):
    """Get events for a session, optionally starting from a sequence number.

    Useful for reconnection: client sends the last sequence number it received,
    and gets all subsequent events.
    """
    manager = _get_manager(request)
    session = manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    events = manager.get_events(session_id)
    return {"events": events[since:]}
