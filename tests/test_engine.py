"""Tests for the deliberation engine."""

import pytest

from colloquip.config import EnergyConfig, ObserverConfig
from colloquip.energy import EnergyCalculator
from colloquip.engine import EmergentDeliberationEngine
from colloquip.llm.mock import MockBehavior, MockLLM
from colloquip.models import (
    AgentStance,
    ConsensusMap,
    EnergyUpdate,
    HumanIntervention,
    Phase,
    PhaseSignal,
    Post,
    SessionStatus,
)
from colloquip.observer import ObserverAgent

from tests.conftest import create_session
from colloquip.cli import create_default_agents


def _create_engine(
    behavior: MockBehavior = MockBehavior.MIXED,
    seed: int = 42,
    max_turns: int = 15,
    min_posts: int = 6,
) -> EmergentDeliberationEngine:
    """Helper to create a test engine."""
    llm = MockLLM(behavior=behavior, seed=seed)
    agents = create_default_agents(llm)
    energy_calc = EnergyCalculator(config=EnergyConfig(min_posts=min_posts, max_posts=30))
    observer = ObserverAgent(energy_calculator=energy_calc, config=ObserverConfig())
    return EmergentDeliberationEngine(
        agents=agents,
        observer=observer,
        energy_calculator=energy_calc,
        llm=llm,
        max_turns=max_turns,
        min_posts=min_posts,
    )


class TestSeedPhase:
    @pytest.mark.asyncio
    async def test_seed_produces_posts(self):
        engine = _create_engine()
        session = create_session()
        events = []
        async for event in engine.run_deliberation(session, session.hypothesis):
            events.append(event)
            if len([e for e in events if isinstance(e, Post)]) >= 6:
                break  # Got seed posts, stop for this test

        posts = [e for e in events if isinstance(e, Post)]
        assert len(posts) >= 6  # One per agent
        agents = {p.agent_id for p in posts}
        assert "biology" in agents
        assert "chemistry" in agents
        assert "redteam" in agents


class TestMainLoop:
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_full_deliberation_completes(self):
        """Full deliberation runs and produces consensus."""
        engine = _create_engine(max_turns=15, min_posts=6)
        session = create_session()
        events = []
        async for event in engine.run_deliberation(session, session.hypothesis):
            events.append(event)

        posts = [e for e in events if isinstance(e, Post)]
        phase_signals = [e for e in events if isinstance(e, PhaseSignal)]
        energy_updates = [e for e in events if isinstance(e, EnergyUpdate)]
        consensus = [e for e in events if isinstance(e, ConsensusMap)]

        assert len(posts) >= 6  # At least seed phase
        assert len(phase_signals) > 0
        assert len(energy_updates) > 0
        assert len(consensus) == 1
        assert session.status == SessionStatus.COMPLETED

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_max_turns_cap(self):
        """Deliberation respects max_turns."""
        engine = _create_engine(
            behavior=MockBehavior.HIGH_NOVELTY,
            max_turns=5,
            min_posts=3,
        )
        session = create_session()
        events = []
        async for event in engine.run_deliberation(session, session.hypothesis):
            events.append(event)

        # Should complete (consensus produced)
        consensus = [e for e in events if isinstance(e, ConsensusMap)]
        assert len(consensus) == 1

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_diverse_stances_in_output(self):
        """Posts should have diverse stances."""
        engine = _create_engine(max_turns=10, min_posts=6)
        session = create_session()
        events = []
        async for event in engine.run_deliberation(session, session.hypothesis):
            events.append(event)

        posts = [e for e in events if isinstance(e, Post)]
        stances = {p.stance for p in posts}
        # With mixed behavior, we should see at least 2 different stances
        assert len(stances) >= 2

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_energy_updates_present(self):
        """Energy updates should be emitted."""
        engine = _create_engine(max_turns=10, min_posts=6)
        session = create_session()
        events = []
        async for event in engine.run_deliberation(session, session.hypothesis):
            events.append(event)

        energy_updates = [e for e in events if isinstance(e, EnergyUpdate)]
        assert len(energy_updates) > 0
        for eu in energy_updates:
            assert 0.0 <= eu.energy <= 1.0


class TestConsensus:
    @pytest.mark.asyncio
    async def test_consensus_map_structure(self):
        engine = _create_engine(max_turns=5, min_posts=3)
        session = create_session()
        events = []
        async for event in engine.run_deliberation(session, session.hypothesis):
            events.append(event)

        consensus = [e for e in events if isinstance(e, ConsensusMap)]
        assert len(consensus) == 1
        cm = consensus[0]
        assert cm.session_id == session.id
        assert cm.summary  # Non-empty
        assert isinstance(cm.final_stances, dict)

    @pytest.mark.asyncio
    async def test_empty_synthesis_guard(self):
        """Synthesis with empty posts returns a fallback message."""
        from colloquip.models import DeliberationSession

        engine = _create_engine(max_turns=0, min_posts=3)
        session = DeliberationSession(hypothesis="Test")
        # Directly test _run_synthesis with empty posts
        consensus = await engine._run_synthesis(session, "Test", [])
        assert consensus.session_id == session.id
        assert "No posts" in consensus.summary


class TestMockBounds:
    def test_declining_novelty_stays_above_minimum(self):
        """DECLINING mode should never produce novelty below 0.05."""
        mock = MockLLM(behavior=MockBehavior.DECLINING, seed=42)
        for _ in range(50):
            mock._call_count += 1
            novelty = mock._pick_novelty()
            assert novelty >= 0.05, f"Novelty {novelty} dropped below 0.05"

    def test_high_novelty_bounds(self):
        mock = MockLLM(behavior=MockBehavior.HIGH_NOVELTY, seed=42)
        for _ in range(50):
            novelty = mock._pick_novelty()
            assert 0.6 <= novelty <= 0.95

    def test_low_novelty_bounds(self):
        mock = MockLLM(behavior=MockBehavior.LOW_NOVELTY, seed=42)
        for _ in range(50):
            novelty = mock._pick_novelty()
            assert 0.05 <= novelty <= 0.3


class TestHandleIntervention:
    """Tests for human intervention handling."""

    @pytest.mark.asyncio
    async def test_question_intervention_creates_posts(self):
        engine = _create_engine(max_turns=5, min_posts=6)
        session = create_session()

        # Build some posts first by running a few turns
        posts = []
        energy_history = []
        async for event in engine.run_deliberation(session, session.hypothesis):
            if isinstance(event, Post):
                posts.append(event)
            elif isinstance(event, EnergyUpdate):
                energy_history.append(event.energy)
            if len(posts) >= 6:
                break

        intervention = HumanIntervention(
            session_id=session.id,
            type="question",
            content="What about the blood-brain barrier crossing?",
        )
        result = await engine.handle_intervention(
            session, intervention, posts, energy_history
        )

        # Should return human post + agent responses
        assert len(result) >= 1
        assert result[0].agent_id == "human"
        assert result[0].content == "What about the blood-brain barrier crossing?"
        assert result[0].stance == AgentStance.NEUTRAL

    @pytest.mark.asyncio
    async def test_terminate_intervention_returns_empty(self):
        engine = _create_engine(max_turns=5, min_posts=6)
        session = create_session()

        energy_history = [0.5, 0.6]
        posts = []

        intervention = HumanIntervention(
            session_id=session.id,
            type="terminate",
            content="Stop deliberation",
        )
        result = await engine.handle_intervention(
            session, intervention, posts, energy_history
        )

        assert result == []
        # Energy should be set to 0 for termination
        assert energy_history[-1] == 0.0

    @pytest.mark.asyncio
    async def test_intervention_injects_energy(self):
        engine = _create_engine(max_turns=5, min_posts=6)
        session = create_session()

        energy_history = [0.3]

        intervention = HumanIntervention(
            session_id=session.id,
            type="data",
            content="New clinical trial data shows significant improvement.",
        )
        # Need some posts for the engine to work with
        posts = []
        async for event in engine.run_deliberation(session, session.hypothesis):
            if isinstance(event, Post):
                posts.append(event)
            if len(posts) >= 6:
                break

        energy_before = energy_history[-1]
        await engine.handle_intervention(
            session, intervention, posts, energy_history
        )

        # Energy should have been injected (boosted)
        assert energy_history[-1] >= energy_before
