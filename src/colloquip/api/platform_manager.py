"""Platform manager: ties together registry, tools, and subreddit management.

This is the in-memory orchestrator for the platform layer. It manages:
- Agent registry (global pool)
- Subreddit configurations
- Tool registry
- Thread creation within subreddits
"""

import logging
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from colloquip.cost_tracker import CostTracker
from colloquip.models import (
    BaseAgentIdentity,
    ParticipationModel,
    ThinkingType,
)
from colloquip.output_templates import get_template
from colloquip.registry import AgentRegistry
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
