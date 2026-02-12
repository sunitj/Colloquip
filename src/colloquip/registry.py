"""Agent registry: global pool of agents, expertise matching, and recruitment.

The registry is the central authority for agent lifecycle:
- Maintains the global pool of persistent agents
- Finds agents by expertise for subreddit recruitment
- Creates new agents only when no matching expertise exists
- Enforces mandatory red team presence in every subreddit
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Set
from uuid import UUID

from colloquip.models import (
    BaseAgentIdentity,
    ExpertiseGap,
    RecruitmentResult,
    SubredditMembership,
    SubredditRole,
)

logger = logging.getLogger(__name__)

# Red team persona template — specialized per subreddit topic
_RED_TEAM_ROLE_TEMPLATE = (
    "As the Red Team agent for this community, your role is to challenge "
    "assumptions, surface uncomfortable truths, and prevent premature consensus. "
    "You are especially focused on: {focus_areas}."
)

# Domain-specific red team focus areas
_DOMAIN_FOCUS_AREAS = {
    "drug_discovery": (
        "safety signals, translational failures, regulatory precedent that "
        "contradicts optimistic claims, historical program failures in this space"
    ),
    "biology": (
        "reproducibility concerns, model organism limitations, confounding variables, "
        "publication bias, oversimplified mechanistic narratives"
    ),
    "chemistry": (
        "synthetic feasibility overestimates, scaffold liability, PAINS compounds, "
        "SAR interpretations that ignore confounders"
    ),
    "protein_engineering": (
        "expression system artifacts, stability-activity tradeoffs that are glossed over, "
        "directed evolution biases, assay artifacts"
    ),
    "synthetic_biology": (
        "chassis organism limitations, genetic circuit reliability, metabolic burden, "
        "scale-up failures, biosafety concerns"
    ),
    "default": (
        "hidden assumptions, failure modes, premature consensus, historical "
        "counterexamples, overlooked risks"
    ),
}


def _compute_overlap(set_a: Set[str], set_b: Set[str]) -> float:
    """Compute Jaccard-like overlap between two sets. Returns 0-1."""
    if not set_a or not set_b:
        return 0.0
    intersection = set_a & set_b
    union = set_a | set_b
    return len(intersection) / len(union) if union else 0.0


def _token_overlap(text_a: str, tokens_b: Set[str]) -> float:
    """Compute overlap between a string (tokenized) and a token set."""
    tokens_a = set(text_a.lower().replace("_", " ").split())
    return _compute_overlap(tokens_a, tokens_b)


class AgentRegistry:
    """Global agent pool. Agents are reused across subreddits.

    The registry loads agents from curated YAML personas and stores them
    in memory. When a subreddit is created, agents are recruited from this pool.
    New agents are only created if no existing agent has matching expertise.
    """

    def __init__(self):
        self._pool: Dict[UUID, BaseAgentIdentity] = {}
        self._by_type: Dict[str, UUID] = {}  # agent_type -> id

    @property
    def pool_size(self) -> int:
        return len(self._pool)

    def list_agents(self) -> List[BaseAgentIdentity]:
        """List all agents in the pool."""
        return list(self._pool.values())

    def get_agent(self, agent_id: UUID) -> Optional[BaseAgentIdentity]:
        """Get an agent by UUID."""
        return self._pool.get(agent_id)

    def get_agent_by_type(self, agent_type: str) -> Optional[BaseAgentIdentity]:
        """Get an agent by agent_type string."""
        uid = self._by_type.get(agent_type)
        if uid:
            return self._pool.get(uid)
        return None

    def register_agent(self, agent: BaseAgentIdentity) -> BaseAgentIdentity:
        """Add an agent to the pool. Returns the agent (idempotent)."""
        if agent.id in self._pool:
            return self._pool[agent.id]

        # Check for duplicate agent_type
        if agent.agent_type in self._by_type:
            existing_id = self._by_type[agent.agent_type]
            logger.warning(
                "Agent type '%s' already registered (id=%s). Returning existing.",
                agent.agent_type, existing_id,
            )
            return self._pool[existing_id]

        self._pool[agent.id] = agent
        self._by_type[agent.agent_type] = agent.id
        logger.info("Registered agent: %s (%s)", agent.display_name, agent.agent_type)
        return agent

    def load_from_personas(self, personas_dir: Optional[Path] = None):
        """Load all curated personas into the pool."""
        from colloquip.agents.persona_loader import load_agent_identities

        agents = load_agent_identities(personas_dir)
        for agent in agents:
            self.register_agent(agent)
        logger.info("Loaded %d agents from persona files", len(agents))

    def find_by_expertise(
        self,
        expertise: str,
        min_score: float = 0.15,
    ) -> List[tuple]:
        """Find agents matching an expertise requirement.

        Returns list of (agent, score) sorted by score descending.
        Scoring:
        - Exact agent_type match: +0.5
        - Expertise tag overlap: +0.3 per matching tag
        - Domain keyword token overlap: +0.2
        """
        expertise_lower = expertise.lower().strip()
        expertise_tokens = set(expertise_lower.replace("_", " ").split())

        scored = []
        for agent in self._pool.values():
            score = 0.0

            # Exact type match
            if agent.agent_type.lower() == expertise_lower:
                score += 0.5

            # Expertise tag overlap
            agent_tags = {t.lower() for t in agent.expertise_tags}
            for token in expertise_tokens:
                if any(token in tag for tag in agent_tags):
                    score += 0.3

            # Domain keyword token overlap
            agent_keywords = {k.lower() for k in agent.domain_keywords}
            kw_overlap = _compute_overlap(expertise_tokens, agent_keywords)
            score += kw_overlap * 0.2

            # Knowledge scope overlap
            agent_scope = {s.lower() for s in agent.knowledge_scope}
            scope_overlap = _compute_overlap(expertise_tokens, agent_scope)
            score += scope_overlap * 0.1

            if score >= min_score:
                scored.append((agent, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored

    def find_or_create(
        self,
        expertise: str,
        domain_keywords: Optional[List[str]] = None,
        knowledge_scope: Optional[List[str]] = None,
        persona_prompt: Optional[str] = None,
        is_red_team: bool = False,
    ) -> BaseAgentIdentity:
        """Find an existing agent with matching expertise, or create a new one.

        1. Exact agent_type match → return existing
        2. High expertise score (>= 0.3) → return best match
        3. No match → create new agent
        """
        # Try exact match first
        existing = self.get_agent_by_type(expertise)
        if existing:
            return existing

        # Try fuzzy match
        matches = self.find_by_expertise(expertise, min_score=0.3)
        if matches:
            best_agent, best_score = matches[0]
            logger.info(
                "Found existing agent '%s' for expertise '%s' (score=%.2f)",
                best_agent.agent_type, expertise, best_score,
            )
            return best_agent

        # Create new agent
        agent = BaseAgentIdentity(
            agent_type=expertise,
            display_name=expertise.replace("_", " ").title(),
            expertise_tags=[expertise],
            persona_prompt=persona_prompt or f"You are the {expertise} expert.",
            domain_keywords=domain_keywords or [],
            knowledge_scope=knowledge_scope or [],
            is_red_team=is_red_team,
        )
        return self.register_agent(agent)

    def find_red_team_agents(self) -> List[BaseAgentIdentity]:
        """Find all red team agents in the pool."""
        return [a for a in self._pool.values() if a.is_red_team]

    def recruit_for_subreddit(
        self,
        required_expertise: List[str],
        subreddit_id: UUID,
        subreddit_domain: str = "default",
        optional_expertise: Optional[List[str]] = None,
    ) -> RecruitmentResult:
        """Recruit agents from the pool for a subreddit.

        For each required expertise, finds the best matching agent.
        Always ensures at least one red team agent is included.
        Reports gaps for missing expertise.
        """
        memberships: List[SubredditMembership] = []
        gaps: List[ExpertiseGap] = []
        recruited_ids: Set[UUID] = set()

        # Recruit for required expertise
        for expertise in required_expertise:
            matches = self.find_by_expertise(expertise, min_score=0.15)
            placed = False
            for agent, score in matches:
                if agent.id not in recruited_ids:
                    membership = SubredditMembership(
                        agent_id=agent.id,
                        subreddit_id=subreddit_id,
                        role=SubredditRole.RED_TEAM if agent.is_red_team else SubredditRole.MEMBER,
                    )
                    memberships.append(membership)
                    recruited_ids.add(agent.id)
                    placed = True
                    break

            if not placed:
                # Check if we have a curated persona for this
                has_template = self.get_agent_by_type(expertise) is not None
                gaps.append(ExpertiseGap(
                    expertise=expertise,
                    domain=subreddit_domain,
                    has_curated_template=has_template,
                ))

        # Recruit optional expertise (best-effort)
        for expertise in (optional_expertise or []):
            matches = self.find_by_expertise(expertise, min_score=0.2)
            for agent, score in matches:
                if agent.id not in recruited_ids:
                    membership = SubredditMembership(
                        agent_id=agent.id,
                        subreddit_id=subreddit_id,
                        role=SubredditRole.MEMBER,
                    )
                    memberships.append(membership)
                    recruited_ids.add(agent.id)
                    break

        # Ensure red team
        has_red_team = any(
            m.role == SubredditRole.RED_TEAM for m in memberships
        )
        if not has_red_team:
            red_team_membership = self._recruit_red_team(
                subreddit_id, subreddit_domain, recruited_ids,
            )
            if red_team_membership:
                memberships.append(red_team_membership)

        return RecruitmentResult(memberships=memberships, gaps=gaps)

    def _recruit_red_team(
        self,
        subreddit_id: UUID,
        domain: str,
        already_recruited: Set[UUID],
    ) -> Optional[SubredditMembership]:
        """Find and recruit a red team agent for the subreddit."""
        red_team_agents = self.find_red_team_agents()

        # Prefer domain-specific red team if available
        for agent in red_team_agents:
            if domain in agent.agent_type and agent.id not in already_recruited:
                return SubredditMembership(
                    agent_id=agent.id,
                    subreddit_id=subreddit_id,
                    role=SubredditRole.RED_TEAM,
                    role_prompt=self._build_red_team_role_prompt(domain),
                )

        # Fall back to general red team
        for agent in red_team_agents:
            if agent.id not in already_recruited:
                return SubredditMembership(
                    agent_id=agent.id,
                    subreddit_id=subreddit_id,
                    role=SubredditRole.RED_TEAM,
                    role_prompt=self._build_red_team_role_prompt(domain),
                )

        # No red team agents exist — log warning
        logger.warning("No red team agents in pool for subreddit %s", subreddit_id)
        return None

    def _build_red_team_role_prompt(self, domain: str) -> str:
        """Build a topic-specific red team role prompt."""
        focus = _DOMAIN_FOCUS_AREAS.get(domain, _DOMAIN_FOCUS_AREAS["default"])
        return _RED_TEAM_ROLE_TEMPLATE.format(focus_areas=focus)
