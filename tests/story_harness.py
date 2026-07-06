"""Shared harness for applied-science user-story e2e tests.

The user stories in ``test_user_stories.py`` double as a feature showcase and a
regression suite. They run against the deterministic ``MockLLM`` by default so
CI stays fast, but can be pointed at the real Anthropic API by setting
``COLLOQUIP_USE_REAL_LLM=1`` (which also requires ``ANTHROPIC_API_KEY``).

This module provides the plumbing every story reuses:

- ``make_llm`` — the mock/real toggle
- ``build_agent`` / ``build_engine`` — thin builders over the production classes
- ``run_story`` + ``StoryRun`` — iterate ``run_deliberation`` and collect the
  typed event stream into a structure that's convenient to assert on
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set
from uuid import UUID, uuid4

from colloquip.agents.base import BaseDeliberationAgent
from colloquip.approvals import ApprovalQueue
from colloquip.autoresearch import MockAutoresearchLoop
from colloquip.cost_tracker import CostTracker
from colloquip.energy import EnergyCalculator
from colloquip.engine import EmergentDeliberationEngine
from colloquip.llm.mock import MockBehavior, MockLLM
from colloquip.models import (
    AgentBudgetSkipped,
    AgentConfig,
    AutoresearchConfig,
    ConsensusMap,
    DeliberationSession,
    EnergyUpdate,
    MissionObjective,
    Phase,
    PhaseSignal,
    Post,
)
from colloquip.observer import ObserverAgent
from colloquip.subreddit_mission import parse_objectives

USE_REAL_LLM = os.environ.get("COLLOQUIP_USE_REAL_LLM", "0") == "1"
REAL_LLM_MODEL = os.environ.get("COLLOQUIP_REAL_LLM_MODEL", "claude-sonnet-4-20250514")


def make_llm(*, behavior: MockBehavior = MockBehavior.MIXED, seed: int = 42):
    """Return an ``AnthropicLLM`` in real mode, otherwise a seeded ``MockLLM``.

    Real mode is opt-in via ``COLLOQUIP_USE_REAL_LLM=1`` and requires
    ``ANTHROPIC_API_KEY``. Behavior/seed are ignored in real mode.
    """
    if USE_REAL_LLM:
        from colloquip.llm.anthropic import AnthropicLLM

        return AnthropicLLM(model=REAL_LLM_MODEL, max_tokens=1024)
    return MockLLM(behavior=behavior, seed=seed)


def build_agent(
    agent_id: str,
    display_name: str,
    persona: str,
    keywords: List[str],
    *,
    scope: Optional[List[str]] = None,
    is_red_team: bool = False,
    autoresearch: bool = False,
    llm=None,
    mock_behavior: MockBehavior = MockBehavior.MIXED,
    seed: int = 42,
) -> BaseDeliberationAgent:
    """Build a deliberation agent from a domain persona.

    ``autoresearch=True`` attaches a ``MockAutoresearchLoop`` so the agent runs
    the Karpathy-style research loop in ``Phase.DEEPEN`` before posting.
    """
    config = AgentConfig(
        agent_id=agent_id,
        display_name=display_name,
        persona_prompt=persona,
        phase_mandates={},
        domain_keywords=keywords,
        knowledge_scope=scope or keywords[:3],
        is_red_team=is_red_team,
        autoresearch_enabled=autoresearch,
    )
    agent_llm = llm or make_llm(behavior=mock_behavior, seed=seed)
    return BaseDeliberationAgent(
        config=config,
        llm=agent_llm,
        autoresearch_loop=MockAutoresearchLoop() if autoresearch else None,
        autoresearch_config=(
            AutoresearchConfig(max_steps=3, max_tokens=2000) if autoresearch else None
        ),
    )


def build_engine(
    agents: Dict[str, BaseDeliberationAgent],
    *,
    session_id: Optional[UUID] = None,
    subreddit_id: Optional[UUID] = None,
    mission_md: Optional[str] = None,
    objectives: Optional[List[MissionObjective]] = None,
    agent_budgets: Optional[Dict[str, float]] = None,
    monthly_budgets: Optional[Dict[str, float]] = None,
    monthly_used: Optional[Dict[str, float]] = None,
    approval_queue: Optional[ApprovalQueue] = None,
    cost_tracker: Optional[CostTracker] = None,
    usage_callback=None,
    max_turns: int = 8,
    min_posts: int = 6,
    max_cost_per_thread_usd: Optional[float] = None,
) -> EmergentDeliberationEngine:
    """Wire an ``EmergentDeliberationEngine`` with sensible observer/energy defaults."""
    sid = session_id or uuid4()
    ct = cost_tracker if cost_tracker is not None else CostTracker()
    ct.start_tracking(sid)
    num_agents = len(agents)
    energy_calc = EnergyCalculator(num_agents=num_agents)
    observer = ObserverAgent(energy_calculator=energy_calc, num_agents=num_agents)

    parsed = objectives
    if parsed is None and mission_md:
        parsed = parse_objectives(mission_md)

    return EmergentDeliberationEngine(
        agents=agents,
        observer=observer,
        energy_calculator=energy_calc,
        llm=make_llm(),
        max_turns=max_turns,
        min_posts=min_posts,
        cost_tracker=ct,
        session_id=sid,
        subreddit_id=subreddit_id,
        subreddit_mission=mission_md,
        mission_objectives=parsed,
        max_cost_per_thread_usd=max_cost_per_thread_usd,
        agent_budgets=agent_budgets,
        agent_monthly_budgets=monthly_budgets,
        agent_monthly_used=monthly_used,
        usage_callback=usage_callback,
        approval_queue=approval_queue,
    )


@dataclass
class StoryRun:
    """Structured collection of everything a deliberation emitted."""

    posts: List[Post] = field(default_factory=list)
    phase_signals: List[PhaseSignal] = field(default_factory=list)
    energy_updates: List[EnergyUpdate] = field(default_factory=list)
    budget_skips: List[AgentBudgetSkipped] = field(default_factory=list)
    consensus: Optional[ConsensusMap] = None

    def agents_that_posted(self) -> Set[str]:
        return {p.agent_id for p in self.posts if p.agent_id != "human"}

    def phases_reached(self) -> Set[Phase]:
        return {s.current_phase for s in self.phase_signals}

    def final_energy(self) -> float:
        return self.energy_updates[-1].energy if self.energy_updates else 0.0

    def energy_series(self) -> List[float]:
        return [e.energy for e in self.energy_updates]

    def posts_by_agent(self, agent_id: str) -> List[Post]:
        return [p for p in self.posts if p.agent_id == agent_id]

    def red_team_rule_posts(self) -> List[Post]:
        rules = {"consensus_forming", "criticism_gap", "premature_convergence"}
        return [p for p in self.posts if rules.intersection(p.triggered_by)]

    def human_posts(self) -> List[Post]:
        return [p for p in self.posts if p.agent_id == "human"]

    def total_citations(self) -> int:
        return sum(len(p.citations) for p in self.posts)


async def run_story(
    engine: EmergentDeliberationEngine,
    session: DeliberationSession,
    hypothesis: str,
) -> StoryRun:
    """Drive ``run_deliberation`` to completion, collecting the event stream."""
    result = StoryRun()
    async for event in engine.run_deliberation(session, hypothesis):
        if isinstance(event, Post):
            result.posts.append(event)
        elif isinstance(event, PhaseSignal):
            result.phase_signals.append(event)
        elif isinstance(event, EnergyUpdate):
            result.energy_updates.append(event)
        elif isinstance(event, AgentBudgetSkipped):
            result.budget_skips.append(event)
        elif isinstance(event, ConsensusMap):
            result.consensus = event
    return result
