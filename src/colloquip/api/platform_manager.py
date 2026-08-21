"""Platform manager: ties together registry, tools, and subreddit management.

This is the in-memory orchestrator for the platform layer. It manages:
- Agent registry (global pool)
- Subreddit configurations
- Tool registry
- Thread creation within subreddits
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from colloquip.approvals import ApprovalQueue
from colloquip.cost_tracker import CostTracker
from colloquip.models import (
    BaseAgentIdentity,
    MissionObjective,
    ObjectiveProgress,
    OrgChart,
    OrgChartEdge,
    OrgChartNode,
    ParticipationModel,
    Post,
    SubredditMission,
    SubredditRole,
    ThinkingType,
)
from colloquip.output_templates import get_template
from colloquip.registry import AgentRegistry
from colloquip.subreddit_mission import measure_objectives, parse_objectives
from colloquip.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)


class PlatformManager:
    """Central orchestrator for the platform layer.

    Manages subreddits, agents, and tools in memory. Can optionally
    persist to the database via a SessionRepository.
    """

    def __init__(self, mock_mode: bool = True):
        self.registry = AgentRegistry()
        self.tool_registry = ToolRegistry(mock_mode=mock_mode)
        self.cost_tracker = CostTracker()
        # Phase 6: Paperclip-style approval queue
        self.approval_queue = ApprovalQueue()

        # In-memory storage (mirrors DB for real-time access)
        self._subreddits: Dict[str, dict] = {}  # id -> subreddit dict
        self._subreddits_by_name: Dict[str, str] = {}  # name -> id
        self._memberships: Dict[str, List[dict]] = {}  # subreddit_id -> [membership dicts]
        self._threads: Dict[str, List[dict]] = {}  # subreddit_id -> [thread dicts]
        self._agent_subreddit_count: Dict[UUID, int] = {}

        self._initialized = False
        # Phase 6: optional DB persistence. When attached, mutations also
        # write through to the SessionRepository, and approval queue
        # enqueue/resolve callbacks persist to the approval_requests table.
        self._db_factory: Optional[Any] = None
        self.approval_queue.subscribe(self._on_approval_event)
        # Optional Buzz mirror (see colloquip.buzz). None = adapter disabled.
        self._buzz: Optional[Any] = None

    def attach_db(self, db_session_factory: Any) -> None:
        """Attach an async session factory so mutations persist to the DB.

        Called from the FastAPI ``lifespan`` startup hook once the engine
        is created. Without this, the platform manager runs in pure in-memory
        mode and mission/budget/approval state is lost on restart.
        """
        self._db_factory = db_session_factory

    def attach_buzz(self, mirror: Any) -> None:
        """Mirror communities and their agent rosters to a Buzz relay.

        Creating a subreddit then also creates the backing Buzz channel,
        publishes a ``kind:0`` profile per recruited agent, and adds each of
        them to the channel as a member.
        """
        self._buzz = mirror

    def _mirror_community(self, subreddit: Dict[str, Any], memberships: List[dict]) -> None:
        """Project a freshly created subreddit onto the Buzz relay."""
        if not self._buzz:
            return
        agents = []
        for membership in memberships:
            try:
                identity = self.registry.get_agent(UUID(membership["agent_id"]))
            except (KeyError, TypeError, ValueError):
                continue
            if not identity:
                continue
            agents.append(
                {
                    # Must match Post.agent_id, which carries agent_type.
                    "agent_id": identity.agent_type,
                    "display_name": identity.display_name,
                    "about": identity.persona_prompt,
                }
            )
        try:
            self._buzz.register_community_nowait(
                subreddit["id"],
                subreddit.get("display_name") or subreddit["name"],
                subreddit.get("description", ""),
                agents,
            )
        except Exception:  # noqa: BLE001 - mirroring must never fail a create
            logger.exception("Could not mirror community '%s' to Buzz", subreddit.get("name"))

    @asynccontextmanager
    async def _open_repo(self):
        """Yield a SessionRepository, committing on success.

        Returns ``None`` (via the ``yielded`` value) when no DB factory has
        been attached, so callers can short-circuit cleanly.
        """
        if not self._db_factory:
            yield None
            return
        from colloquip.db.repository import SessionRepository

        async with self._db_factory() as db:
            repo = SessionRepository(db)
            try:
                yield repo
                await repo.commit()
            except Exception:
                logger.exception("PlatformManager DB write failed")
                raise

    def _on_approval_event(self, event: str, request) -> None:
        """ApprovalQueue subscriber: schedule a DB persist for the change."""
        if self._db_factory is None:
            return
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            return
        if not loop.is_running():
            return
        # Fire-and-forget: persist the request without blocking the queue.
        loop.create_task(self._persist_approval(request))

    async def _persist_approval(self, request) -> None:
        try:
            async with self._open_repo() as repo:
                if repo is None:
                    return
                await repo.save_approval_request(request)
        except Exception:  # noqa: BLE001
            logger.exception("Failed to persist approval request %s", request.id)

    def initialize(self):
        """Load personas into registry. Idempotent."""
        if self._initialized:
            return
        self.registry.load_from_personas()
        self._initialized = True
        logger.info(
            "Platform initialized: %d agents in pool",
            self.registry.pool_size,
        )

    # ---- Subreddits ----

    def create_subreddit(
        self,
        name: str,
        display_name: str,
        description: str = "",
        thinking_type: ThinkingType = ThinkingType.ASSESSMENT,
        core_questions: Optional[List[str]] = None,
        decision_context: str = "",
        primary_domain: str = "drug_discovery",
        required_expertise: Optional[List[str]] = None,
        optional_expertise: Optional[List[str]] = None,
        participation_model: ParticipationModel = ParticipationModel.GUIDED,
        tool_ids: Optional[List[str]] = None,
        max_cost_per_thread_usd: float = 5.0,
        max_agents: int = 8,
    ) -> Dict[str, Any]:
        """Create a subreddit, recruit agents, and configure tools."""
        self.initialize()

        subreddit_id = str(uuid4())

        # Get output template for thinking type
        template = get_template(thinking_type)

        # Build tool configs
        tool_configs = []
        for tool_id in tool_ids or []:
            if tool_id in self.tool_registry.available_tools():
                tool_configs.append(
                    {
                        "tool_id": tool_id,
                        "display_name": tool_id.replace("_", " ").title(),
                        "description": f"Search via {tool_id}",
                        "tool_type": "literature_search",
                        "connection_config": {},
                        "enabled": True,
                    }
                )

        # Build purpose
        purpose = {
            "thinking_type": thinking_type.value,
            "core_questions": core_questions or [],
            "decision_context": decision_context,
            "primary_domain": primary_domain,
            "required_expertise": required_expertise or [],
            "optional_expertise": optional_expertise or [],
        }

        subreddit = {
            "id": subreddit_id,
            "name": name,
            "display_name": display_name,
            "description": description,
            "purpose": purpose,
            "output_template": template.model_dump(),
            "participation_model": participation_model.value,
            "tool_configs": tool_configs,
            "max_cost_per_thread_usd": max_cost_per_thread_usd,
            "max_agents": max_agents,
            "always_include_red_team": True,
            # Phase 6: subreddit-level mission directive + parsed objectives
            "mission_md": None,
            "mission_objectives": [],
            "mission_version": 1,
            "mission_updated_at": None,
        }

        # Store
        self._subreddits[subreddit_id] = subreddit
        self._subreddits_by_name[name] = subreddit_id
        self._memberships[subreddit_id] = []
        self._threads[subreddit_id] = []

        # Recruit agents — auto-infer expertise from domain when none provided
        effective_expertise = list(required_expertise or [])
        if not effective_expertise:
            # Use primary_domain to find all matching non-red-team agents
            domain_matches = self.registry.find_by_expertise(
                primary_domain.replace("_", " "), min_score=0.1
            )
            for agent, _score in domain_matches:
                if not agent.is_red_team and agent.agent_type not in effective_expertise:
                    effective_expertise.append(agent.agent_type)
            # If domain search yields nothing, recruit all non-red-team agents
            if not effective_expertise:
                for agent in self.registry.list_agents():
                    if not agent.is_red_team:
                        effective_expertise.append(agent.agent_type)

        recruitment = self.registry.recruit_for_subreddit(
            required_expertise=effective_expertise,
            subreddit_id=UUID(subreddit_id),
            subreddit_domain=primary_domain,
            optional_expertise=optional_expertise,
            max_agents=max_agents,
        )

        # Store memberships
        for m in recruitment.memberships:
            self._memberships[subreddit_id].append(
                {
                    "id": str(m.id),
                    "agent_id": str(m.agent_id),
                    "subreddit_id": subreddit_id,
                    "role": m.role.value,
                    "role_prompt": m.role_prompt,
                    "tool_access": [tc["tool_id"] for tc in tool_configs],
                }
            )
            # Track count
            self._agent_subreddit_count[m.agent_id] = (
                self._agent_subreddit_count.get(m.agent_id, 0) + 1
            )

        self._mirror_community(subreddit, self._memberships[subreddit_id])

        return {
            "subreddit": subreddit,
            "recruitment": recruitment,
        }

    def get_subreddit(self, subreddit_id: str) -> Optional[dict]:
        return self._subreddits.get(subreddit_id)

    def get_subreddit_by_name(self, name: str) -> Optional[dict]:
        sid = self._subreddits_by_name.get(name)
        if sid:
            return self._subreddits.get(sid)
        return None

    def list_subreddits(self) -> List[dict]:
        return list(self._subreddits.values())

    def get_subreddit_members(self, subreddit_id: str) -> List[dict]:
        """Get members with agent details."""
        memberships = self._memberships.get(subreddit_id, [])
        result = []
        for m in memberships:
            agent = self.registry.get_agent(UUID(m["agent_id"]))
            entry = dict(m)
            if agent:
                entry["agent_type"] = agent.agent_type
                entry["display_name"] = agent.display_name
                entry["is_red_team"] = agent.is_red_team
                entry["expertise_tags"] = agent.expertise_tags
            result.append(entry)
        return result

    def get_subreddit_threads(self, subreddit_id: str) -> List[dict]:
        return self._threads.get(subreddit_id, [])

    # ---- Phase 6: Subreddit mission ----

    def get_subreddit_mission(self, subreddit_id: str) -> Optional[SubredditMission]:
        subreddit = self._subreddits.get(subreddit_id)
        if not subreddit:
            return None
        objectives_raw = subreddit.get("mission_objectives") or []
        objectives: List[MissionObjective] = []
        for raw in objectives_raw:
            try:
                objectives.append(MissionObjective(**raw))
            except Exception:
                continue
        return SubredditMission(
            subreddit_id=UUID(subreddit_id),
            mission_md=subreddit.get("mission_md"),
            objectives=objectives,
            version=subreddit.get("mission_version") or 1,
            updated_at=subreddit.get("mission_updated_at"),
        )

    def update_subreddit_mission(
        self,
        subreddit_id: str,
        mission_md: Optional[str],
        objectives: Optional[List[MissionObjective]] = None,
    ) -> Optional[SubredditMission]:
        """Update a subreddit's mission markdown; re-parse objectives if omitted.

        When a DB factory is attached, the write is mirrored to the
        ``subreddits`` table via ``SessionRepository.update_subreddit_mission``.
        """
        subreddit = self._subreddits.get(subreddit_id)
        if not subreddit:
            return None
        parsed = objectives if objectives is not None else parse_objectives(mission_md)
        subreddit["mission_md"] = mission_md
        subreddit["mission_objectives"] = [obj.model_dump(mode="json") for obj in parsed]
        subreddit["mission_version"] = (subreddit.get("mission_version") or 1) + 1
        subreddit["mission_updated_at"] = datetime.now(timezone.utc)
        self._fire_persist(self._persist_subreddit_mission(subreddit_id, mission_md, parsed))
        return self.get_subreddit_mission(subreddit_id)

    async def _persist_subreddit_mission(
        self,
        subreddit_id: str,
        mission_md: Optional[str],
        objectives: List[MissionObjective],
    ) -> None:
        try:
            async with self._open_repo() as repo:
                if repo is None:
                    return
                await repo.update_subreddit_mission(
                    subreddit_id=subreddit_id,
                    mission_md=mission_md,
                    objectives=objectives,
                )
        except Exception:  # noqa: BLE001
            logger.exception("Failed to persist mission for %s", subreddit_id)

    def _fire_persist(self, coro) -> None:
        """Schedule an async persistence task without blocking the caller.

        Used by sync mutators (update_subreddit_mission, set_member_budget)
        so existing callers don't have to become async. When called from
        non-async context (e.g. unit tests with no running loop), the coro
        is closed cleanly instead of being scheduled.
        """
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            coro.close()
            return
        if not loop.is_running():
            coro.close()
            return
        loop.create_task(coro)

    def set_member_budget(
        self,
        subreddit_id: str,
        agent_id: str,
        max_cost_per_thread_usd: Optional[float] = None,
        monthly_budget_usd: Optional[float] = None,
    ) -> Optional[dict]:
        """Update a single member's per-thread and/or monthly budget.

        Mirrored to ``subreddit_memberships`` via the repository when a DB
        factory is attached.
        """
        memberships = self._memberships.get(subreddit_id, [])
        for m in memberships:
            if m.get("agent_id") == agent_id:
                if max_cost_per_thread_usd is not None:
                    m["max_cost_per_thread_usd"] = max_cost_per_thread_usd
                if monthly_budget_usd is not None:
                    m["monthly_budget_usd"] = monthly_budget_usd
                self._fire_persist(
                    self._persist_member_budget(
                        subreddit_id=subreddit_id,
                        agent_id=agent_id,
                        max_cost_per_thread_usd=max_cost_per_thread_usd,
                        monthly_budget_usd=monthly_budget_usd,
                    )
                )
                return m
        return None

    async def _persist_member_budget(
        self,
        subreddit_id: str,
        agent_id: str,
        max_cost_per_thread_usd: Optional[float],
        monthly_budget_usd: Optional[float],
    ) -> None:
        try:
            async with self._open_repo() as repo:
                if repo is None:
                    return
                await repo.update_member_budget(
                    subreddit_id=subreddit_id,
                    agent_id=agent_id,
                    max_cost_per_thread_usd=max_cost_per_thread_usd,
                    monthly_budget_usd=monthly_budget_usd,
                )
        except Exception:  # noqa: BLE001
            logger.exception("Failed to persist budget for %s/%s", subreddit_id, agent_id)

    def get_member_budgets(self, subreddit_id: str) -> Dict[str, float]:
        """Return a ``{agent_type: max_cost_per_thread_usd}`` map for an engine."""
        budgets: Dict[str, float] = {}
        for m in self._memberships.get(subreddit_id, []):
            cap = m.get("max_cost_per_thread_usd")
            if cap is None:
                continue
            agent_uuid = m.get("agent_id")
            if not agent_uuid:
                continue
            agent = self.registry.get_agent(UUID(agent_uuid))
            if agent:
                budgets[agent.agent_type] = float(cap)
        return budgets

    def get_member_monthly_budgets(self, subreddit_id: str) -> Dict[str, float]:
        """Return a ``{agent_type: monthly_budget_usd}`` map for an engine."""
        budgets: Dict[str, float] = {}
        for m in self._memberships.get(subreddit_id, []):
            cap = m.get("monthly_budget_usd")
            if cap is None:
                continue
            agent_uuid = m.get("agent_id")
            if not agent_uuid:
                continue
            agent = self.registry.get_agent(UUID(agent_uuid))
            if agent:
                budgets[agent.agent_type] = float(cap)
        return budgets

    def get_member_monthly_used(self, subreddit_id: str) -> Dict[str, float]:
        """Return ``{agent_type: current_month_cost_usd}`` from in-memory cache.

        When DB is attached, this is hydrated from the membership rows on
        startup; otherwise it's the in-memory accumulation.
        """
        used: Dict[str, float] = {}
        for m in self._memberships.get(subreddit_id, []):
            current = m.get("current_month_cost_usd")
            if current is None:
                continue
            agent_uuid = m.get("agent_id")
            if not agent_uuid:
                continue
            agent = self.registry.get_agent(UUID(agent_uuid))
            if agent:
                used[agent.agent_type] = float(current)
        return used

    async def accumulate_usage(
        self,
        subreddit_id: str,
        agent_type: str,
        input_tokens: int,
        output_tokens: int,
        cost_usd: float,
    ) -> None:
        """Update the in-memory membership's lifetime/monthly counters and
        mirror to the DB if attached.

        Called from the engine ``usage_callback`` after every LLM invocation.
        """
        agent_uuid: Optional[str] = None
        for m in self._memberships.get(subreddit_id, []):
            aid = m.get("agent_id")
            if not aid:
                continue
            try:
                agent = self.registry.get_agent(UUID(aid))
            except Exception:  # noqa: BLE001
                continue
            if agent and agent.agent_type == agent_type:
                m["lifetime_cost_usd"] = float(m.get("lifetime_cost_usd", 0.0)) + cost_usd
                m["lifetime_input_tokens"] = int(m.get("lifetime_input_tokens", 0)) + input_tokens
                m["lifetime_output_tokens"] = (
                    int(m.get("lifetime_output_tokens", 0)) + output_tokens
                )
                m["current_month_cost_usd"] = float(m.get("current_month_cost_usd", 0.0)) + cost_usd
                agent_uuid = aid
                break
        if agent_uuid is None or self._db_factory is None:
            return
        try:
            async with self._open_repo() as repo:
                if repo is None:
                    return
                await repo.accumulate_member_usage(
                    subreddit_id=subreddit_id,
                    agent_id=agent_uuid,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    cost_usd=cost_usd,
                )
        except Exception:  # noqa: BLE001
            logger.exception("Failed to persist usage for %s/%s", subreddit_id, agent_type)

    # ---- Phase 6: Org chart + goal progress ----

    def get_subreddit_org_chart(
        self,
        subreddit_id: str,
        recent_posts: Optional[List[Post]] = None,
    ) -> Optional[OrgChart]:
        """Build an org-chart view for a subreddit.

        Nodes are the subreddit's members; edges are either explicit
        ``reports_to`` relationships (from membership overrides) or the
        aggregated ``triggered_by`` signals from recent posts (aggregated
        per agent pair by the caller).
        """
        if subreddit_id not in self._subreddits:
            return None
        members = self.get_subreddit_members(subreddit_id)

        # agent_type -> (agent_id_str, node)
        nodes_by_type: Dict[str, OrgChartNode] = {}
        for m in members:
            agent_type = m.get("agent_type")
            if not agent_type:
                continue
            reports_to = m.get("reports_to_agent_id")
            role_value = m.get("role", "member")
            try:
                role = SubredditRole(role_value)
            except ValueError:
                role = SubredditRole.MEMBER
            node = OrgChartNode(
                agent_id=agent_type,
                display_name=m.get("display_name") or agent_type,
                role=role,
                reports_to=reports_to,
                lifetime_cost_usd=float(m.get("lifetime_cost_usd", 0.0) or 0.0),
                is_red_team=bool(m.get("is_red_team", False)),
            )
            nodes_by_type[agent_type] = node

        edges: List[OrgChartEdge] = []
        # reports_to edges
        for agent_type, node in nodes_by_type.items():
            if node.reports_to and node.reports_to in nodes_by_type:
                edges.append(
                    OrgChartEdge(
                        from_agent_id=agent_type,
                        to_agent_id=node.reports_to,
                        edge_type="reports_to",
                        weight=1.0,
                    )
                )

        # triggered_by edges (aggregated from recent posts)
        if recent_posts:
            counter: Dict[tuple[str, str], int] = {}
            post_counts: Dict[str, int] = {}
            for post in recent_posts:
                post_counts[post.agent_id] = post_counts.get(post.agent_id, 0) + 1
                for trigger in post.triggered_by or []:
                    # trigger rules may be keyed like "responded_to:<agent_id>"
                    if ":" in trigger:
                        _, source = trigger.split(":", 1)
                    else:
                        source = None
                    if source and source != post.agent_id:
                        key = (source, post.agent_id)
                        counter[key] = counter.get(key, 0) + 1
            for (src, dst), weight in counter.items():
                if src in nodes_by_type and dst in nodes_by_type:
                    edges.append(
                        OrgChartEdge(
                            from_agent_id=src,
                            to_agent_id=dst,
                            edge_type="triggered",
                            weight=float(weight),
                        )
                    )
            for agent_id, count in post_counts.items():
                node = nodes_by_type.get(agent_id)
                if node:
                    node.post_count = count

        return OrgChart(
            subreddit_id=UUID(subreddit_id),
            nodes=list(nodes_by_type.values()),
            edges=edges,
        )

    def measure_subreddit_mission_progress(
        self,
        subreddit_id: str,
        recent_posts: Optional[List[Post]] = None,
    ) -> List[ObjectiveProgress]:
        """Score current mission objectives for a subreddit."""
        mission = self.get_subreddit_mission(subreddit_id)
        if not mission:
            return []
        return measure_objectives(mission.objectives, recent_posts or [])

    # ---- Agents ----

    def list_agents(self) -> List[BaseAgentIdentity]:
        return self.registry.list_agents()

    def get_agent_subreddit_count(self, agent_id: UUID) -> int:
        return self._agent_subreddit_count.get(agent_id, 0)

    # ---- Threads ----

    def create_thread(
        self,
        subreddit_id: str,
        title: str,
        hypothesis: str,
        mode: str = "mock",
        seed: int = 42,
        model: Optional[str] = None,
        max_turns: int = 30,
        thread_id: Optional[str] = None,
    ) -> dict:
        """Create a deliberation thread within a subreddit.

        This creates the thread metadata and delegates to SessionManager
        for the actual deliberation engine setup.
        """
        thread_id = thread_id or str(uuid4())
        thread = {
            "id": thread_id,
            "subreddit_id": subreddit_id,
            "title": title,
            "hypothesis": hypothesis,
            "status": "pending",
            "phase": "explore",
            "mode": mode,
            "seed": seed,
            "model": model,
            "max_turns": max_turns,
        }

        self._threads.setdefault(subreddit_id, []).append(thread)

        return thread

    def update_thread_status(
        self,
        thread_id: str,
        status: Optional[str] = None,
        phase: Optional[str] = None,
        post_count: Optional[int] = None,
    ) -> None:
        """Update an existing thread's status/phase/post_count in-place."""
        for threads in self._threads.values():
            for thread in threads:
                if thread["id"] == thread_id:
                    if status is not None:
                        thread["status"] = status
                    if phase is not None:
                        thread["phase"] = phase
                    if post_count is not None:
                        thread["post_count"] = post_count
                    return

    # ---- Costs ----

    def get_thread_costs(self, thread_id: str) -> dict:
        """Get cost information for a thread via the CostTracker."""
        try:
            tid = UUID(thread_id)
        except ValueError:
            return {
                "thread_id": thread_id,
                "total_input_tokens": 0,
                "total_output_tokens": 0,
                "estimated_cost_usd": 0.0,
                "num_llm_calls": 0,
            }
        return self.cost_tracker.thread_summary(tid)
