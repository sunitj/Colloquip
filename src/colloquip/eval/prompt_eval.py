"""Prompt evaluation harness.

Runs a mock deliberation with a given prompt version and computes
quality metrics. Works entirely with MockLLM — no API key required.
When a real LLM is available, the same harness can be used to compare
prompt versions against actual Claude output.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set

from colloquip.agents.base import BaseDeliberationAgent
from colloquip.config import EnergyConfig
from colloquip.energy import EnergyCalculator
from colloquip.engine import EmergentDeliberationEngine
from colloquip.llm.mock import MockBehavior, MockLLM
from colloquip.models import (
    AgentConfig,
    ConsensusMap,
    DeliberationSession,
    EnergyUpdate,
    Phase,
    Post,
)
from colloquip.observer import ObserverAgent


@dataclass
class PromptEvalResult:
    """Quality metrics from a single evaluation run."""

    prompt_version: str
    seed: int
    total_posts: int = 0
    total_turns: int = 0

    # Diversity metrics
    stance_diversity: int = 0  # distinct stances seen
    unique_stances: Set[str] = field(default_factory=set)
    agents_that_posted: Set[str] = field(default_factory=set)

    # Content richness
    avg_claims_per_post: float = 0.0
    avg_questions_per_post: float = 0.0
    avg_connections_per_post: float = 0.0

    # Phase coverage
    phases_reached: Set[str] = field(default_factory=set)
    phase_transitions: int = 0

    # Energy dynamics
    energy_curve: List[float] = field(default_factory=list)
    energy_declined_naturally: bool = False
    final_energy: float = 0.0

    # Red Team
    red_team_posted: bool = False
    red_team_post_count: int = 0

    # Consensus
    has_consensus: bool = False
    consensus_agreements: int = 0
    consensus_disagreements: int = 0

    def summary_dict(self) -> Dict:
        """Return a flat dict suitable for table display."""
        return {
            "version": self.prompt_version,
            "seed": self.seed,
            "posts": self.total_posts,
            "agents": len(self.agents_that_posted),
            "stances": self.stance_diversity,
            "claims/post": f"{self.avg_claims_per_post:.1f}",
            "questions/post": f"{self.avg_questions_per_post:.1f}",
            "phases": len(self.phases_reached),
            "transitions": self.phase_transitions,
            "red_team": self.red_team_post_count,
            "energy_declined": self.energy_declined_naturally,
            "consensus": self.has_consensus,
        }


def _create_agents(llm, prompt_version: str = "v1") -> Dict[str, BaseDeliberationAgent]:
    """Create default agents with a specific prompt version."""
    from colloquip.cli import DEFAULT_AGENTS, MINIMAL_PERSONAS

    agents = {}
    for agent_id, agent_data in DEFAULT_AGENTS.items():
        config = AgentConfig(
            agent_id=agent_id,
            display_name=agent_data["display_name"],
            persona_prompt=MINIMAL_PERSONAS[agent_id],
            phase_mandates={},
            domain_keywords=agent_data["domain_keywords"],
            knowledge_scope=agent_data["knowledge_scope"],
            is_red_team=agent_data["is_red_team"],
        )
        agents[agent_id] = BaseDeliberationAgent(
            config=config, llm=llm, prompt_version=prompt_version
        )
    return agents


async def evaluate_prompt_version(
    prompt_version: str = "v1",
    seed: int = 42,
    max_turns: int = 20,
    behavior: MockBehavior = MockBehavior.MIXED,
) -> PromptEvalResult:
    """Run a full deliberation and compute quality metrics."""
    result = PromptEvalResult(prompt_version=prompt_version, seed=seed)

    llm = MockLLM(behavior=behavior, seed=seed)
    agents = _create_agents(llm, prompt_version)
    num_agents = len(agents)

    energy_config = EnergyConfig()
    energy_calc = EnergyCalculator(config=energy_config)
    observer = ObserverAgent(energy_calculator=energy_calc, num_agents=num_agents)

    engine = EmergentDeliberationEngine(
        agents=agents,
        observer=observer,
        energy_calculator=energy_calc,
        llm=llm,
        max_turns=max_turns,
        min_posts=12,
    )

    session = DeliberationSession(
        hypothesis="GLP-1 agonists may improve cognitive function in Alzheimer's patients"
    )

    posts: List[Post] = []
    prev_phase: Optional[Phase] = None

    async for event in engine.run_deliberation(session, session.hypothesis):
        if isinstance(event, Post):
            posts.append(event)
            result.agents_that_posted.add(event.agent_id)
            result.unique_stances.add(event.stance.value)
            result.phases_reached.add(event.phase.value)

            if event.agent_id == "redteam":
                result.red_team_posted = True
                result.red_team_post_count += 1

            if prev_phase is not None and event.phase != prev_phase:
                result.phase_transitions += 1
            prev_phase = event.phase

        elif isinstance(event, EnergyUpdate):
            result.energy_curve.append(event.energy)

        elif isinstance(event, ConsensusMap):
            result.has_consensus = True
            result.consensus_agreements = len(event.agreements)
            result.consensus_disagreements = len(event.disagreements)

    # Compute aggregate metrics
    result.total_posts = len(posts)
    result.stance_diversity = len(result.unique_stances)

    if posts:
        result.avg_claims_per_post = sum(len(p.key_claims) for p in posts) / len(posts)
        result.avg_questions_per_post = sum(len(p.questions_raised) for p in posts) / len(posts)
        result.avg_connections_per_post = sum(len(p.connections_identified) for p in posts) / len(
            posts
        )

    if result.energy_curve:
        result.final_energy = result.energy_curve[-1]
        # Energy declined if peak > final by at least 0.1
        peak = max(result.energy_curve)
        result.energy_declined_naturally = (peak - result.final_energy) >= 0.1

    return result


async def compare_versions(
    versions: Optional[List[str]] = None,
    seed: int = 42,
    max_turns: int = 20,
) -> List[PromptEvalResult]:
    """Run evaluation for multiple prompt versions and return results."""
    if versions is None:
        from colloquip.agents.prompts import PROMPT_VERSIONS

        versions = list(PROMPT_VERSIONS.keys())

    results = []
    for version in versions:
        result = await evaluate_prompt_version(
            prompt_version=version,
            seed=seed,
            max_turns=max_turns,
        )
        results.append(result)
    return results
