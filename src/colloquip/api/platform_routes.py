"""Platform API routes for subreddits, agents, and threads.

These extend the existing deliberation API with the social platform
capabilities. All new endpoints are under /api/subreddits and /api/agents.
"""

import logging
from typing import TYPE_CHECKING, List, Literal, Optional
from uuid import UUID

if TYPE_CHECKING:
    from colloquip.api.platform_manager import PlatformManager
    from colloquip.models import RecruitmentResult

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from colloquip.models import (
    ParticipationModel,
    ThinkingType,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------


class CreateSubredditRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100, pattern=r"^[a-z0-9_]+$")
    display_name: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=2000)
    thinking_type: ThinkingType = ThinkingType.ASSESSMENT
    core_questions: List[str] = Field(default_factory=list)
    decision_context: str = ""
    primary_domain: str = "drug_discovery"
    required_expertise: List[str] = Field(default_factory=list)
    optional_expertise: List[str] = Field(default_factory=list)
    participation_model: ParticipationModel = ParticipationModel.GUIDED
    tool_ids: List[str] = Field(default_factory=list)
    max_cost_per_thread_usd: float = 5.0
    max_agents: int = Field(default=8, ge=2, le=15)


class SubredditResponse(BaseModel):
    id: str
    name: str
    display_name: str
    description: str
    thinking_type: str
    participation_model: str
    member_count: int
    thread_count: int
    tool_ids: List[str]
    has_red_team: bool


class SubredditDetailResponse(SubredditResponse):
    core_questions: List[str]
    decision_context: str
    primary_domain: str
    members: List[dict]
    recruitment_gaps: List[dict]
    max_cost_per_thread_usd: float


class AgentResponse(BaseModel):
    id: str
    agent_type: str
    display_name: str
    expertise_tags: List[str]
    is_red_team: bool
    subreddit_count: int


class CreateThreadRequest(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    hypothesis: str = Field(min_length=1, max_length=5000)
    mode: Literal["mock", "real"] = "mock"
    seed: int = 42
    model: Optional[str] = None
    max_turns: int = Field(default=30, ge=1, le=100)
    thread_id: Optional[str] = None


class ThreadResponse(BaseModel):
    id: str
    subreddit_id: str
    subreddit_name: str
    title: str
    hypothesis: str
    status: str
    phase: str
    post_count: int
    estimated_cost_usd: float


class HumanPostRequest(BaseModel):
    content: str = Field(min_length=1, max_length=5000)
    post_type: Literal["comment", "question", "data", "redirect"] = "comment"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_platform(request: Request):
    """Get the PlatformManager from app state, ensuring it's initialized."""
    pm = getattr(request.app.state, "platform_manager", None)
    if pm is None:
        raise HTTPException(
            status_code=503,
            detail="Platform not initialized. Use /api/platform/init first.",
        )
    if not pm._initialized:
        raise HTTPException(
            status_code=503,
            detail="Platform not initialized. Call POST /api/platform/init first.",
        )
    return pm


# ---------------------------------------------------------------------------
# Subreddit endpoints
# ---------------------------------------------------------------------------


@router.post("/subreddits", response_model=SubredditDetailResponse)
async def create_subreddit(body: CreateSubredditRequest, request: Request):
    """Create a new subreddit with auto-recruited agents."""
    pm = _get_platform(request)

    # Check name uniqueness
    existing = pm.get_subreddit_by_name(body.name)
    if existing:
        raise HTTPException(status_code=409, detail=f"Subreddit '{body.name}' already exists")

    result = pm.create_subreddit(
        name=body.name,
        display_name=body.display_name,
        description=body.description,
        thinking_type=body.thinking_type,
        core_questions=body.core_questions,
        decision_context=body.decision_context,
        primary_domain=body.primary_domain,
        required_expertise=body.required_expertise,
        optional_expertise=body.optional_expertise,
        participation_model=body.participation_model,
        tool_ids=body.tool_ids,
        max_cost_per_thread_usd=body.max_cost_per_thread_usd,
        max_agents=body.max_agents,
    )

    return _build_subreddit_detail_response(pm, result["subreddit"], result["recruitment"])


@router.get("/subreddits", response_model=List[SubredditResponse])
async def list_subreddits(request: Request):
    """List all subreddits."""
    pm = _get_platform(request)
    subreddits = pm.list_subreddits()
    return [_build_subreddit_response(pm, s) for s in subreddits]


@router.get("/subreddits/{name}", response_model=SubredditDetailResponse)
async def get_subreddit(name: str, request: Request):
    """Get subreddit details including roster and tools."""
    pm = _get_platform(request)
    subreddit = pm.get_subreddit_by_name(name)
    if not subreddit:
        raise HTTPException(status_code=404, detail=f"Subreddit '{name}' not found")
    return _build_subreddit_detail_response(pm, subreddit)


@router.get("/subreddits/{name}/members")
async def get_subreddit_members(name: str, request: Request):
    """List agents in a subreddit."""
    pm = _get_platform(request)
    subreddit = pm.get_subreddit_by_name(name)
    if not subreddit:
        raise HTTPException(status_code=404, detail=f"Subreddit '{name}' not found")

    members = pm.get_subreddit_members(subreddit["id"])
    return {"members": members}


@router.get("/subreddits/{name}/threads")
async def list_subreddit_threads(name: str, request: Request):
    """List threads in a subreddit."""
    pm = _get_platform(request)
    subreddit = pm.get_subreddit_by_name(name)
    if not subreddit:
        raise HTTPException(status_code=404, detail=f"Subreddit '{name}' not found")

    threads = pm.get_subreddit_threads(subreddit["id"])
    return {"threads": threads}


@router.post("/subreddits/{name}/threads", response_model=ThreadResponse)
async def create_thread(name: str, body: CreateThreadRequest, request: Request):
    """Create a new deliberation thread in a subreddit."""
    pm = _get_platform(request)
    subreddit = pm.get_subreddit_by_name(name)
    if not subreddit:
        raise HTTPException(status_code=404, detail=f"Subreddit '{name}' not found")

    thread = pm.create_thread(
        subreddit_id=subreddit["id"],
        title=body.title,
        hypothesis=body.hypothesis,
        mode=body.mode,
        seed=body.seed,
        model=body.model,
        max_turns=body.max_turns,
        thread_id=body.thread_id,
    )

    return ThreadResponse(
        id=str(thread["id"]),
        subreddit_id=subreddit["id"],
        subreddit_name=name,
        title=body.title,
        hypothesis=body.hypothesis,
        status=thread["status"],
        phase=thread.get("phase", "explore"),
        post_count=0,
        estimated_cost_usd=0.0,
    )


# ---------------------------------------------------------------------------
# Agent endpoints
# ---------------------------------------------------------------------------


@router.get("/agents", response_model=List[AgentResponse])
async def list_agents(request: Request):
    """List all agents in the global pool."""
    pm = _get_platform(request)
    agents = pm.list_agents()
    return [
        AgentResponse(
            id=str(a.id),
            agent_type=a.agent_type,
            display_name=a.display_name,
            expertise_tags=a.expertise_tags,
            is_red_team=a.is_red_team,
            subreddit_count=pm.get_agent_subreddit_count(a.id),
        )
        for a in agents
    ]


@router.get("/agents/{agent_id}")
async def get_agent(agent_id: str, request: Request):
    """Get agent details including subreddit memberships."""
    pm = _get_platform(request)
    try:
        agent_uuid = UUID(agent_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid agent ID format")

    agent = pm.registry.get_agent(agent_uuid)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    return {
        "id": str(agent.id),
        "agent_type": agent.agent_type,
        "display_name": agent.display_name,
        "expertise_tags": agent.expertise_tags,
        "domain_keywords": agent.domain_keywords,
        "knowledge_scope": agent.knowledge_scope,
        "persona_prompt": agent.persona_prompt,
        "phase_mandates": {
            k.value if hasattr(k, "value") else k: v for k, v in agent.phase_mandates.items()
        },
        "evaluation_criteria": list(agent.evaluation_criteria.keys()),
        "is_red_team": agent.is_red_team,
        "status": agent.status.value,
        "version": agent.version,
    }


# ---------------------------------------------------------------------------
# Cost endpoints
# ---------------------------------------------------------------------------


@router.get("/threads/{thread_id}/costs")
async def get_thread_costs(thread_id: str, request: Request):
    """Get cost breakdown for a thread."""
    try:
        UUID(thread_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid thread ID format")
    pm = _get_platform(request)
    costs = pm.get_thread_costs(thread_id)
    return costs


# ---------------------------------------------------------------------------
# Platform init
# ---------------------------------------------------------------------------


@router.post("/platform/init")
async def init_platform(request: Request):
    """Initialize the platform — loads personas and creates default subreddits.

    Idempotent: safe to call multiple times.
    """
    pm = _get_platform_or_create(request)
    pm.initialize()
    return {
        "status": "initialized",
        "agents_loaded": pm.registry.pool_size,
        "subreddits": len(pm.list_subreddits()),
    }


def _get_platform_or_create(request: Request):
    """Get or create the PlatformManager."""
    from colloquip.api.platform_manager import PlatformManager

    pm = getattr(request.app.state, "platform_manager", None)
    if pm is None:
        pm = PlatformManager()
        request.app.state.platform_manager = pm
    return pm


# ---------------------------------------------------------------------------
# Response builders
# ---------------------------------------------------------------------------


def _subreddit_common(pm: "PlatformManager", subreddit: dict) -> tuple:
    """Shared data extraction for subreddit responses."""
    members = pm.get_subreddit_members(subreddit["id"])
    has_red_team = any(m.get("role") == "red_team" for m in members)
    threads = pm.get_subreddit_threads(subreddit["id"])
    purpose = subreddit.get("purpose", {})
    tool_ids = [tc.get("tool_id", "") for tc in (subreddit.get("tool_configs") or [])]
    return members, has_red_team, threads, purpose, tool_ids


def _build_subreddit_response(pm: "PlatformManager", subreddit: dict) -> SubredditResponse:
    members, has_red_team, threads, purpose, tool_ids = _subreddit_common(pm, subreddit)
    return SubredditResponse(
        id=subreddit["id"],
        name=subreddit["name"],
        display_name=subreddit["display_name"],
        description=subreddit.get("description", ""),
        thinking_type=purpose.get("thinking_type", "assessment"),
        participation_model=subreddit.get("participation_model", "guided"),
        member_count=len(members),
        thread_count=len(threads),
        tool_ids=tool_ids,
        has_red_team=has_red_team,
    )


def _build_subreddit_detail_response(
    pm: "PlatformManager",
    subreddit: dict,
    recruitment: Optional["RecruitmentResult"] = None,
) -> SubredditDetailResponse:
    members, has_red_team, threads, purpose, tool_ids = _subreddit_common(pm, subreddit)
    gaps = (
        [g.model_dump() for g in recruitment.gaps]
        if recruitment and hasattr(recruitment, "gaps")
        else []
    )
    return SubredditDetailResponse(
        id=subreddit["id"],
        name=subreddit["name"],
        display_name=subreddit["display_name"],
        description=subreddit.get("description", ""),
        thinking_type=purpose.get("thinking_type", "assessment"),
        participation_model=subreddit.get("participation_model", "guided"),
        member_count=len(members),
        thread_count=len(threads),
        tool_ids=tool_ids,
        has_red_team=has_red_team,
        core_questions=purpose.get("core_questions", []),
        decision_context=purpose.get("decision_context", ""),
        primary_domain=purpose.get("primary_domain", ""),
        members=members,
        recruitment_gaps=gaps,
        max_cost_per_thread_usd=subreddit.get("max_cost_per_thread_usd", 5.0),
    )
