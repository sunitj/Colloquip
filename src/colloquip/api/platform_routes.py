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
    ApprovalRequestType,
    ApprovalStatus,
    MissionObjective,
    ParticipationModel,
    ThinkingType,
)
from colloquip.subreddit_mission import parse_objectives

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
    """List threads in a subreddit, enriched with live session data."""
    pm = _get_platform(request)
    subreddit = pm.get_subreddit_by_name(name)
    if not subreddit:
        raise HTTPException(status_code=404, detail=f"Subreddit '{name}' not found")

    threads = pm.get_subreddit_threads(subreddit["id"])
    sm = getattr(request.app.state, "session_manager", None)

    enriched = []
    for thread in threads:
        t = dict(thread)
        t.setdefault("subreddit_name", name)
        t.setdefault("post_count", 0)
        t.setdefault("estimated_cost_usd", 0.0)

        if sm:
            thread_id = t["id"]
            try:
                sid = UUID(thread_id)
            except ValueError:
                enriched.append(t)
                continue

            # 1. Check in-memory session for live data
            session = sm.get_session(sid)
            if session:
                t["status"] = session.status.value
                t["phase"] = session.phase.value
                t["post_count"] = len(sm.get_posts(sid))
            else:
                # 2. DB fallback for fixture-loaded threads
                try:
                    data = await sm.load_session_data(sid)
                    if data and data.get("session"):
                        db_session = data["session"]
                        t["status"] = db_session.status.value
                        t["phase"] = db_session.phase.value
                        t["post_count"] = len(data.get("posts", []))
                except Exception:
                    pass  # Keep PlatformManager defaults

            # Costs from CostTracker
            costs = pm.get_thread_costs(thread_id)
            t["estimated_cost_usd"] = costs.get("estimated_cost_usd", 0.0)

        enriched.append(t)
    return {"threads": enriched}


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


# ---------------------------------------------------------------------------
# Phase 6: Subreddit mission + per-agent budgets
# ---------------------------------------------------------------------------


class MissionObjectiveResponse(BaseModel):
    id: str
    title: str
    description: str = ""
    metric: Optional[str] = None
    target: Optional[float] = None
    status: str = "open"


class SubredditMissionResponse(BaseModel):
    subreddit_id: str
    mission_md: Optional[str] = None
    objectives: List[MissionObjectiveResponse] = Field(default_factory=list)
    version: int = 1
    updated_at: Optional[str] = None


class UpdateMissionRequest(BaseModel):
    mission_md: Optional[str] = None
    objectives: Optional[List[MissionObjectiveResponse]] = None
    regenerate_objectives: bool = True


class UpdateMemberBudgetRequest(BaseModel):
    max_cost_per_thread_usd: Optional[float] = Field(default=None, ge=0.0)
    monthly_budget_usd: Optional[float] = Field(default=None, ge=0.0)


@router.get("/subreddits/{name}/mission", response_model=SubredditMissionResponse)
async def get_subreddit_mission(name: str, request: Request):
    """Read the subreddit's program.md-style mission directive + parsed objectives."""
    pm = _get_platform(request)
    subreddit = pm.get_subreddit_by_name(name)
    if not subreddit:
        raise HTTPException(status_code=404, detail=f"Subreddit '{name}' not found")
    mission = pm.get_subreddit_mission(subreddit["id"])
    if not mission:
        return SubredditMissionResponse(subreddit_id=subreddit["id"])
    return SubredditMissionResponse(
        subreddit_id=str(mission.subreddit_id),
        mission_md=mission.mission_md,
        objectives=[MissionObjectiveResponse(**obj.model_dump()) for obj in mission.objectives],
        version=mission.version,
        updated_at=mission.updated_at.isoformat() if mission.updated_at else None,
    )


@router.put("/subreddits/{name}/mission", response_model=SubredditMissionResponse)
async def update_subreddit_mission(name: str, body: UpdateMissionRequest, request: Request):
    """Update the subreddit mission markdown and re-parse objectives.

    If ``regenerate_objectives`` is true (default), objectives are re-parsed
    from the markdown. If ``objectives`` is provided it overrides that.
    """
    pm = _get_platform(request)
    subreddit = pm.get_subreddit_by_name(name)
    if not subreddit:
        raise HTTPException(status_code=404, detail=f"Subreddit '{name}' not found")

    if body.objectives is not None:
        parsed = [MissionObjective(**obj.model_dump()) for obj in body.objectives]
    elif body.regenerate_objectives:
        parsed = parse_objectives(body.mission_md or "")
    else:
        # Preserve existing objectives
        existing = pm.get_subreddit_mission(subreddit["id"])
        parsed = list(existing.objectives) if existing else []

    mission = pm.update_subreddit_mission(
        subreddit["id"], mission_md=body.mission_md, objectives=parsed
    )
    if not mission:
        raise HTTPException(status_code=500, detail="Failed to update mission")
    return SubredditMissionResponse(
        subreddit_id=str(mission.subreddit_id),
        mission_md=mission.mission_md,
        objectives=[MissionObjectiveResponse(**obj.model_dump()) for obj in mission.objectives],
        version=mission.version,
        updated_at=mission.updated_at.isoformat() if mission.updated_at else None,
    )


@router.get("/subreddits/{name}/mission/progress")
async def get_subreddit_mission_progress(name: str, request: Request):
    """Measure progress against a subreddit's mission objectives.

    Aggregates posts from active in-memory sessions to compute each
    quantitative objective. Qualitative objectives are returned with
    ``qualitative=True`` so the UI can surface them for human review.
    """
    pm = _get_platform(request)
    subreddit = pm.get_subreddit_by_name(name)
    if not subreddit:
        raise HTTPException(status_code=404, detail=f"Subreddit '{name}' not found")

    sm = getattr(request.app.state, "session_manager", None)
    recent_posts: list = []
    if sm is not None:
        threads = pm.get_subreddit_threads(subreddit["id"])
        for thread in threads:
            try:
                sid = UUID(thread["id"])
            except (KeyError, ValueError):
                continue
            recent_posts.extend(sm.get_posts(sid))

    progress = pm.measure_subreddit_mission_progress(subreddit["id"], recent_posts=recent_posts)
    return {"objectives": [p.model_dump() for p in progress]}


@router.get("/subreddits/{name}/org-chart")
async def get_subreddit_org_chart(name: str, request: Request):
    """Return the agent org chart (nodes + edges) for a subreddit."""
    pm = _get_platform(request)
    subreddit = pm.get_subreddit_by_name(name)
    if not subreddit:
        raise HTTPException(status_code=404, detail=f"Subreddit '{name}' not found")

    sm = getattr(request.app.state, "session_manager", None)
    recent_posts: list = []
    if sm is not None:
        threads = pm.get_subreddit_threads(subreddit["id"])
        for thread in threads:
            try:
                sid = UUID(thread["id"])
            except (KeyError, ValueError):
                continue
            recent_posts.extend(sm.get_posts(sid))

    chart = pm.get_subreddit_org_chart(subreddit["id"], recent_posts=recent_posts)
    if chart is None:
        raise HTTPException(status_code=404, detail=f"Subreddit '{name}' not found")
    return chart.model_dump(mode="json")


@router.get("/subreddits/{name}/budgets")
async def get_subreddit_budgets(name: str, request: Request):
    """List per-member budgets + current usage for a subreddit."""
    pm = _get_platform(request)
    subreddit = pm.get_subreddit_by_name(name)
    if not subreddit:
        raise HTTPException(status_code=404, detail=f"Subreddit '{name}' not found")

    members = pm.get_subreddit_members(subreddit["id"])
    return {
        "subreddit_id": subreddit["id"],
        "max_cost_per_thread_usd": subreddit.get("max_cost_per_thread_usd"),
        "monthly_budget_usd": subreddit.get("monthly_budget_usd"),
        "members": [
            {
                "agent_id": m.get("agent_id"),
                "agent_type": m.get("agent_type"),
                "display_name": m.get("display_name"),
                "role": m.get("role"),
                "max_cost_per_thread_usd": m.get("max_cost_per_thread_usd"),
                "monthly_budget_usd": m.get("monthly_budget_usd"),
                "lifetime_cost_usd": m.get("lifetime_cost_usd", 0.0),
                "current_month_cost_usd": m.get("current_month_cost_usd", 0.0),
            }
            for m in members
        ],
    }


@router.patch("/subreddits/{name}/members/{agent_id}/budget")
async def update_member_budget(
    name: str, agent_id: str, body: UpdateMemberBudgetRequest, request: Request
):
    """Update a specific member's per-thread or monthly budget override."""
    pm = _get_platform(request)
    subreddit = pm.get_subreddit_by_name(name)
    if not subreddit:
        raise HTTPException(status_code=404, detail=f"Subreddit '{name}' not found")

    updated = pm.set_member_budget(
        subreddit_id=subreddit["id"],
        agent_id=agent_id,
        max_cost_per_thread_usd=body.max_cost_per_thread_usd,
        monthly_budget_usd=body.monthly_budget_usd,
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Membership not found")
    return updated


# ---------------------------------------------------------------------------
# Phase 6: Approval queue
# ---------------------------------------------------------------------------


class ApprovalResponse(BaseModel):
    id: str
    subreddit_id: str
    request_type: str
    initiator: str = ""
    target_ref: Optional[str] = None
    payload: dict = Field(default_factory=dict)
    status: str
    reason: str = ""
    estimated_cost_usd: float = 0.0
    requested_at: str
    decided_at: Optional[str] = None
    decided_by: Optional[str] = None


class EnqueueApprovalRequest(BaseModel):
    request_type: ApprovalRequestType
    initiator: str = ""
    target_ref: Optional[str] = None
    payload: dict = Field(default_factory=dict)
    reason: str = ""
    estimated_cost_usd: float = 0.0


class ResolveApprovalRequest(BaseModel):
    status: ApprovalStatus
    decided_by: Optional[str] = None


def _approval_to_response(req) -> ApprovalResponse:
    return ApprovalResponse(
        id=str(req.id),
        subreddit_id=str(req.subreddit_id),
        request_type=req.request_type.value,
        initiator=req.initiator,
        target_ref=req.target_ref,
        payload=req.payload or {},
        status=req.status.value,
        reason=req.reason,
        estimated_cost_usd=req.estimated_cost_usd,
        requested_at=req.requested_at.isoformat(),
        decided_at=req.decided_at.isoformat() if req.decided_at else None,
        decided_by=req.decided_by,
    )


@router.get("/subreddits/{name}/approvals")
async def list_subreddit_approvals(
    name: str,
    request: Request,
    status: Optional[str] = None,
):
    """List approval requests for a subreddit, optionally filtered by status."""
    pm = _get_platform(request)
    subreddit = pm.get_subreddit_by_name(name)
    if not subreddit:
        raise HTTPException(status_code=404, detail=f"Subreddit '{name}' not found")

    status_enum: Optional[ApprovalStatus] = None
    if status:
        try:
            status_enum = ApprovalStatus(status)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status '{status}'")

    items = pm.approval_queue.list_for_subreddit(subreddit["id"], status=status_enum)
    return {"approvals": [_approval_to_response(r).model_dump() for r in items]}


@router.post("/subreddits/{name}/approvals", response_model=ApprovalResponse)
async def create_subreddit_approval(name: str, body: EnqueueApprovalRequest, request: Request):
    """Manually enqueue an approval request (e.g. from an admin UI)."""
    pm = _get_platform(request)
    subreddit = pm.get_subreddit_by_name(name)
    if not subreddit:
        raise HTTPException(status_code=404, detail=f"Subreddit '{name}' not found")
    req = pm.approval_queue.enqueue(
        subreddit_id=UUID(subreddit["id"]),
        request_type=body.request_type,
        initiator=body.initiator,
        target_ref=body.target_ref,
        payload=body.payload,
        reason=body.reason,
        estimated_cost_usd=body.estimated_cost_usd,
    )
    return _approval_to_response(req)


@router.post("/approvals/{request_id}/resolve", response_model=ApprovalResponse)
async def resolve_approval(request_id: str, body: ResolveApprovalRequest, request: Request):
    """Approve or deny a pending request."""
    pm = _get_platform(request)
    try:
        req_uuid = UUID(request_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid request id")
    req = pm.approval_queue.resolve(req_uuid, body.status, decided_by=body.decided_by)
    if not req:
        raise HTTPException(status_code=404, detail="Approval request not found")
    return _approval_to_response(req)


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
