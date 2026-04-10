"""Phase 6 test: BaseDeliberationAgent integrates the autoresearch layer.

Drives the implementation of the opt-in hook in BaseDeliberationAgent:
when ``config.autoresearch_enabled`` is true (and the gating phase is met),
the agent runs an autoresearch loop before generating its post, attaches the
findings to the user prompt, and exposes the run audit record for persistence.
"""

from uuid import uuid4

import pytest

from colloquip.agents.base import BaseDeliberationAgent
from colloquip.autoresearch import MockAutoresearchLoop
from colloquip.llm.mock import MockBehavior, MockLLM
from colloquip.models import (
    AgentConfig,
    AgentDependencies,
    ConversationMetrics,
    DeliberationSession,
    Phase,
    PhaseSignal,
)


def _make_signal(phase: Phase = Phase.DEEPEN) -> PhaseSignal:
    return PhaseSignal(
        current_phase=phase,
        confidence=0.9,
        metrics=ConversationMetrics(
            question_rate=0.1,
            disagreement_rate=0.1,
            topic_diversity=0.2,
            citation_density=0.1,
            novelty_avg=0.2,
            energy=0.5,
            posts_since_novel=0,
        ),
    )


class _SpyLLM:
    def __init__(self):
        self.inner = MockLLM(behavior=MockBehavior.MIXED, seed=1)
        self.last_system_prompt: str = ""
        self.last_user_prompt: str = ""

    async def generate(self, system_prompt, user_prompt, max_tokens=None):
        self.last_system_prompt = system_prompt
        self.last_user_prompt = user_prompt
        return await self.inner.generate(system_prompt, user_prompt, max_tokens)


@pytest.mark.asyncio
class TestBaseAgentAutoresearch:
    def _make_config(self, autoresearch_enabled: bool) -> AgentConfig:
        return AgentConfig(
            agent_id="adm-et-expert",
            display_name="ADMET Expert",
            persona_prompt="You are an ADMET expert.",
            phase_mandates={p: "" for p in Phase},
            domain_keywords=["pk"],
            knowledge_scope=["pharmacokinetics"],
            autoresearch_enabled=autoresearch_enabled,
        )

    def _make_deps(self) -> AgentDependencies:
        return AgentDependencies(
            session=DeliberationSession(id=uuid4(), hypothesis="GLP-1 improves cognition"),
            phase=Phase.DEEPEN,
            phase_signal=_make_signal(),
            posts=[],
        )

    async def test_autoresearch_disabled_by_default_no_findings(self):
        llm = _SpyLLM()
        agent = BaseDeliberationAgent(
            config=self._make_config(autoresearch_enabled=False),
            llm=llm,
            autoresearch_loop=MockAutoresearchLoop(),
        )
        await agent.generate_post(self._make_deps())
        assert "## Autoresearch Findings" not in llm.last_user_prompt
        assert agent.last_autoresearch_run is None

    async def test_autoresearch_enabled_runs_loop_and_attaches_findings(self):
        llm = _SpyLLM()
        agent = BaseDeliberationAgent(
            config=self._make_config(autoresearch_enabled=True),
            llm=llm,
            autoresearch_loop=MockAutoresearchLoop(),
        )
        await agent.generate_post(self._make_deps())
        assert "## Autoresearch Findings" in llm.last_user_prompt
        assert "Finding" in llm.last_user_prompt
        assert agent.last_autoresearch_run is not None
        assert agent.last_autoresearch_run.agent_id == "adm-et-expert"
        assert len(agent.last_autoresearch_run.steps) > 0

    async def test_autoresearch_skipped_in_explore_phase(self):
        """Gating: only fire in DEEPEN by default to avoid inflating cost."""
        llm = _SpyLLM()
        agent = BaseDeliberationAgent(
            config=self._make_config(autoresearch_enabled=True),
            llm=llm,
            autoresearch_loop=MockAutoresearchLoop(),
        )
        deps = AgentDependencies(
            session=DeliberationSession(id=uuid4(), hypothesis="Test"),
            phase=Phase.EXPLORE,
            phase_signal=_make_signal(Phase.EXPLORE),
            posts=[],
        )
        await agent.generate_post(deps)
        assert "## Autoresearch Findings" not in llm.last_user_prompt
        assert agent.last_autoresearch_run is None
