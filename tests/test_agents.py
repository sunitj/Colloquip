"""Tests for agent prompt building and base agent."""

import pytest

from colloquip.agents.base import BaseDeliberationAgent
from colloquip.agents.prompts import (
    build_synthesis_prompt,
    build_system_prompt,
    build_user_prompt,
)
from colloquip.llm.mock import MockBehavior, MockLLM
from colloquip.models import (
    AgentDependencies,
    AgentStance,
    ConversationMetrics,
    Phase,
    PhaseSignal,
)
from tests.conftest import create_agent_config, create_post, create_session


class TestPromptBuilder:
    def test_system_prompt_includes_persona(self):
        config = create_agent_config()
        prompt = build_system_prompt(config, Phase.EXPLORE)
        assert "Biology" in prompt

    def test_system_prompt_includes_phase_mandate(self):
        config = create_agent_config()
        prompt = build_system_prompt(config, Phase.DEBATE)
        assert "DEBATE" in prompt

    def test_system_prompt_includes_guidelines(self):
        config = create_agent_config()
        prompt = build_system_prompt(config, Phase.EXPLORE)
        assert "Response Format" in prompt

    def test_different_phases_produce_different_prompts(self):
        config = create_agent_config()
        explore_prompt = build_system_prompt(config, Phase.EXPLORE)
        debate_prompt = build_system_prompt(config, Phase.DEBATE)
        assert explore_prompt != debate_prompt

    def test_user_prompt_includes_hypothesis(self):
        prompt = build_user_prompt(
            hypothesis="GLP-1 agonists improve cognition",
            posts=[],
        )
        assert "GLP-1" in prompt

    def test_user_prompt_includes_history(self):
        posts = [
            create_post(content="Test biology content", agent_id="biology"),
            create_post(content="Test chemistry content", agent_id="chemistry"),
        ]
        prompt = build_user_prompt(
            hypothesis="Test hypothesis",
            posts=posts,
        )
        assert "biology" in prompt
        assert "chemistry" in prompt

    def test_synthesis_prompt(self):
        posts = [
            create_post(
                agent_id="biology",
                stance=AgentStance.SUPPORTIVE,
                key_claims=["Claim 1"],
            ),
            create_post(
                agent_id="redteam",
                stance=AgentStance.CRITICAL,
                key_claims=["Counter-claim"],
            ),
        ]
        prompt = build_synthesis_prompt("Test hypothesis", posts)
        assert "Consensus" in prompt
        assert "biology" in prompt
        assert "redteam" in prompt


class TestBaseAgent:
    @pytest.fixture
    def mock_llm(self):
        return MockLLM(behavior=MockBehavior.MIXED, seed=42)

    @pytest.fixture
    def agent(self, mock_llm):
        config = create_agent_config()
        return BaseDeliberationAgent(config=config, llm=mock_llm)

    def test_agent_properties(self, agent):
        assert agent.agent_id == "biology"
        assert agent.display_name == "Biology & Target ID"

    def test_should_respond_delegates_to_trigger(self, agent):
        # Seed phase (empty posts) → should respond
        should, rules = agent.should_respond([], Phase.EXPLORE)
        assert should
        assert "seed_phase" in rules

    @pytest.mark.asyncio
    async def test_generate_post(self, agent):
        session = create_session()
        signal = PhaseSignal(
            current_phase=Phase.EXPLORE,
            confidence=0.9,
            metrics=ConversationMetrics(
                question_rate=0.0,
                disagreement_rate=0.0,
                topic_diversity=0.0,
                citation_density=0.0,
                novelty_avg=0.0,
                energy=1.0,
                posts_since_novel=0,
            ),
        )
        deps = AgentDependencies(
            session=session,
            phase=Phase.EXPLORE,
            phase_signal=signal,
            posts=[],
        )
        post = await agent.generate_post(deps)
        assert post.agent_id == "biology"
        assert post.session_id == session.id
        assert post.content  # Non-empty
        assert post.stance in AgentStance

    @pytest.mark.asyncio
    async def test_fallback_on_llm_failure(self):
        """Agent should produce fallback post if LLM fails."""

        class FailingLLM:
            async def generate(self, system_prompt, user_prompt):
                raise RuntimeError("LLM unavailable")

            async def generate_synthesis(self, system_prompt, user_prompt):
                raise RuntimeError("LLM unavailable")

        config = create_agent_config()
        agent = BaseDeliberationAgent(config=config, llm=FailingLLM())
        session = create_session()
        signal = PhaseSignal(
            current_phase=Phase.EXPLORE,
            confidence=0.9,
            metrics=ConversationMetrics(
                question_rate=0.0,
                disagreement_rate=0.0,
                topic_diversity=0.0,
                citation_density=0.0,
                novelty_avg=0.0,
                energy=1.0,
                posts_since_novel=0,
            ),
        )
        deps = AgentDependencies(
            session=session,
            phase=Phase.EXPLORE,
            phase_signal=signal,
            posts=[],
        )
        post = await agent.generate_post(deps)
        assert post.stance == AgentStance.NEUTRAL
        assert "fallback" in post.triggered_by
