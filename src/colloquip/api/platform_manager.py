"""Platform manager: ties together registry, tools, and subreddit management.

This is the in-memory orchestrator for the platform layer. It manages:
- Agent registry (global pool)
- Subreddit configurations
- Tool registry
- Thread creation within subreddits
"""

import logging
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
        """Update a subreddit's mission markdown; re-parse objectives if omitted."""
        subreddit = self._subreddits.get(subreddit_id)
        if not subreddit:
            return None
        parsed = objectives if objectives is not None else parse_objectives(mission_md)
        subreddit["mission_md"] = mission_md
        subreddit["mission_objectives"] = [obj.model_dump(mode="json") for obj in parsed]
        subreddit["mission_version"] = (subreddit.get("mission_version") or 1) + 1
        subreddit["mission_updated_at"] = datetime.now(timezone.utc)
        return self.get_subreddit_mission(subreddit_id)

    def set_member_budget(
        self,
        subreddit_id: str,
        agent_id: str,
        max_cost_per_thread_usd: Optional[float] = None,
        monthly_budget_usd: Optional[float] = None,
    ) -> Optional[dict]:
        """Update a single member's per-thread and/or monthly budget."""
        memberships = self._memberships.get(subreddit_id, [])
        for m in memberships:
            if m.get("agent_id") == agent_id:
                if max_cost_per_thread_usd is not None:
                    m["max_cost_per_thread_usd"] = max_cost_per_thread_usd
                if monthly_budget_usd is not None:
                    m["monthly_budget_usd"] = monthly_budget_usd
                return m
        return None

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
