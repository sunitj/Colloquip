"""API routes for exporting deliberation results."""

import json
import logging
from typing import Dict, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, PlainTextResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")


# --- Helpers ---

def _parse_uuid(value: str, label: str = "ID") -> UUID:
    try:
        return UUID(value)
    except (ValueError, AttributeError):
        raise HTTPException(status_code=400, detail=f"Invalid {label}: {value!r}")


async def _get_synthesis_data(request: Request, thread_id: str) -> Dict:
    """Retrieve synthesis data for a thread. Returns raw dict."""
    session_manager = getattr(request.app.state, "session_manager", None)
    if session_manager is None:
        raise HTTPException(status_code=503, detail="Session manager not initialized")

    tid = _parse_uuid(thread_id, "thread_id")
    session_data = await session_manager.load_session_data(tid)
    if session_data is None:
        raise HTTPException(status_code=404, detail="Thread not found")
    return session_data


# --- Endpoints ---

@router.get("/threads/{thread_id}/export/markdown")
async def export_markdown(request: Request, thread_id: str) -> PlainTextResponse:
    """Export a deliberation as Markdown."""
    session_data = await _get_synthesis_data(request, thread_id)
    session = session_data["session"]

    lines = []
    lines.append(f"# {session.hypothesis}")
    lines.append(f"\nStatus: {session.status.value}")
    lines.append(f"Phase: {session.phase.value}")
    lines.append(f"Created: {session.created_at.strftime('%Y-%m-%d %H:%M UTC')}")
    lines.append("")

    # Posts
    posts = session_data.get("posts", [])
    if posts:
        lines.append("## Discussion")
        for post in posts:
            lines.append(f"\n### [{post.phase.value}] {post.agent_id}")
            lines.append(f"*Stance: {post.stance.value}*\n")
            lines.append(post.content)
            if post.key_claims:
                lines.append("\n**Key claims:**")
                for claim in post.key_claims:
                    lines.append(f"- {claim}")

    # Consensus
    consensus = session_data.get("consensus")
    if consensus:
        lines.append("\n## Consensus")
        lines.append(consensus.summary)
        if consensus.agreements:
            lines.append("\n### Agreements")
            for a in consensus.agreements:
                lines.append(f"- {a}")
        if consensus.disagreements:
            lines.append("\n### Disagreements")
            for d in consensus.disagreements:
                lines.append(f"- {d}")

    return PlainTextResponse(
        content="\n".join(lines),
        media_type="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="deliberation_{thread_id}.md"'},
    )


@router.get("/threads/{thread_id}/export/json")
async def export_json(request: Request, thread_id: str) -> JSONResponse:
    """Export a deliberation as structured JSON."""
    session_data = await _get_synthesis_data(request, thread_id)
    session = session_data["session"]

    export = {
        "thread_id": str(session.id),
        "hypothesis": session.hypothesis,
        "status": session.status.value,
        "phase": session.phase.value,
        "created_at": session.created_at.isoformat(),
        "posts": [
            {
                "agent_id": p.agent_id,
                "content": p.content,
                "stance": p.stance.value,
                "phase": p.phase.value,
                "key_claims": p.key_claims,
                "novelty_score": p.novelty_score,
                "created_at": p.created_at.isoformat(),
            }
            for p in session_data.get("posts", [])
        ],
        "energy_history": [
            {"turn": e.turn, "energy": e.energy, "components": e.components}
            for e in session_data.get("energy_history", [])
        ],
    }

    consensus = session_data.get("consensus")
    if consensus:
        export["consensus"] = {
            "summary": consensus.summary,
            "agreements": consensus.agreements,
            "disagreements": consensus.disagreements,
            "minority_positions": consensus.minority_positions,
        }

    return JSONResponse(
        content=export,
        headers={"Content-Disposition": f'attachment; filename="deliberation_{thread_id}.json"'},
    )
