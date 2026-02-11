"""Tests for observer agent and phase detection."""

import pytest

from colloquip.models import AgentStance, Citation, Phase
from colloquip.observer import ObserverAgent

from tests.conftest import create_post


class TestMetricCalculation:
    def test_question_rate(self, observer):
        posts = [
            create_post(content="What about the mechanism?"),
            create_post(content="The target shows activity.", agent_id="chemistry"),
            create_post(content="Is this safe?", agent_id="admet"),
        ]
        metrics = observer.calculate_metrics(posts)
        assert metrics.question_rate == pytest.approx(2 / 3, abs=0.01)

    def test_disagreement_rate(self, observer):
        posts = [
            create_post(stance=AgentStance.CRITICAL),
            create_post(stance=AgentStance.CRITICAL, agent_id="chemistry"),
            create_post(stance=AgentStance.SUPPORTIVE, agent_id="admet"),
        ]
        metrics = observer.calculate_metrics(posts)
        assert metrics.disagreement_rate == pytest.approx(2 / 3, abs=0.01)

    def test_topic_diversity(self, observer):
        posts = [
            create_post(agent_id="biology"),
            create_post(agent_id="chemistry"),
            create_post(agent_id="admet"),
            create_post(agent_id="clinical"),
        ]
        metrics = observer.calculate_metrics(posts)
        assert metrics.topic_diversity == pytest.approx(4 / 6, abs=0.01)

    def test_citation_density(self, observer):
        citation = Citation(
            document_id="D1", title="Test", excerpt="Excerpt", relevance=0.9
        )
        posts = [
            create_post(citations=[citation, citation]),
            create_post(citations=[citation], agent_id="chemistry"),
        ]
        metrics = observer.calculate_metrics(posts)
        # 3 citations / (2 posts * 3) = 0.5
        assert metrics.citation_density == pytest.approx(0.5, abs=0.01)

    def test_novelty_average(self, observer):
        posts = [
            create_post(novelty_score=0.8),
            create_post(novelty_score=0.4, agent_id="chemistry"),
        ]
        metrics = observer.calculate_metrics(posts)
        assert metrics.novelty_avg == pytest.approx(0.6, abs=0.01)

    def test_posts_since_novel(self, observer):
        posts = [
            create_post(novelty_score=0.9),  # Novel
            create_post(novelty_score=0.3, agent_id="chemistry"),
            create_post(novelty_score=0.2, agent_id="admet"),
        ]
        metrics = observer.calculate_metrics(posts)
        assert metrics.posts_since_novel == 2


class TestPhaseDetection:
    def test_explore_detected(self, observer):
        """High question rate + diverse agents → EXPLORE."""
        posts = [
            create_post(content="What about the mechanism?", agent_id="biology"),
            create_post(content="What does chemistry say?", agent_id="chemistry"),
            create_post(content="Is there safety data?", agent_id="admet"),
            create_post(content="What are clinical implications?", agent_id="clinical"),
        ]
        signal = observer.detect_phase(posts)
        # First detection — might still be EXPLORE (default) due to hysteresis
        assert signal.current_phase == Phase.EXPLORE

    def test_debate_detected(self, observer):
        """High disagreement + citations → DEBATE after sustained signal."""
        citation = Citation(
            document_id="D1", title="Paper", excerpt="Evidence", relevance=0.9
        )
        debate_posts = [
            create_post(
                stance=AgentStance.CRITICAL,
                citations=[citation, citation],
                agent_id=f"agent_{i}",
            )
            for i in range(6)
        ]

        # Need sustained signal (hysteresis_threshold = 3)
        for _ in range(3):
            signal = observer.detect_phase(debate_posts)
        assert signal.current_phase == Phase.DEBATE

    def test_deepen_detected(self, observer):
        """Focused (low diversity) + high novelty → DEEPEN after hysteresis."""
        posts = [
            create_post(agent_id="biology", novelty_score=0.8),
            create_post(agent_id="biology", novelty_score=0.9),
        ]
        for _ in range(3):
            signal = observer.detect_phase(posts)
        assert signal.current_phase == Phase.DEEPEN

    def test_converge_detected(self, observer):
        """Low energy + stagnating → CONVERGE after hysteresis."""
        posts = [create_post(novelty_score=0.1) for _ in range(15)]
        for _ in range(4):
            signal = observer.detect_phase(posts)
        assert signal.current_phase == Phase.CONVERGE

    def test_ambiguous_metrics_no_change(self, observer):
        """Ambiguous metrics → maintain current phase."""
        # Middle-ground metrics that don't clearly indicate any phase
        posts = [
            create_post(
                content="Some analysis here.",
                agent_id=f"agent_{i % 3}",
                novelty_score=0.4,
                stance=AgentStance.NEUTRAL,
            )
            for i in range(5)
        ]
        signal = observer.detect_phase(posts)
        assert signal.current_phase == Phase.EXPLORE  # Default


class TestHysteresis:
    def test_single_signal_no_transition(self, observer):
        """One signal shouldn't cause phase change."""
        citation = Citation(
            document_id="D1", title="P", excerpt="E", relevance=0.9
        )
        debate_posts = [
            create_post(
                stance=AgentStance.CRITICAL,
                citations=[citation, citation],
                agent_id=f"a{i}",
            )
            for i in range(6)
        ]
        signal = observer.detect_phase(debate_posts)
        assert signal.current_phase == Phase.EXPLORE  # Still default

    def test_three_consecutive_signals_cause_transition(self, observer):
        """Three consecutive signals → transition."""
        citation = Citation(
            document_id="D1", title="P", excerpt="E", relevance=0.9
        )
        debate_posts = [
            create_post(
                stance=AgentStance.CRITICAL,
                citations=[citation, citation],
                agent_id=f"a{i}",
            )
            for i in range(6)
        ]
        for _ in range(2):
            observer.detect_phase(debate_posts)
        signal = observer.detect_phase(debate_posts)
        assert signal.current_phase == Phase.DEBATE

    def test_interrupted_signal_resets_counter(self, observer):
        """Interrupted signal → counter resets, no transition."""
        citation = Citation(
            document_id="D1", title="P", excerpt="E", relevance=0.9
        )
        debate_posts = [
            create_post(
                stance=AgentStance.CRITICAL,
                citations=[citation, citation],
                agent_id=f"a{i}",
            )
            for i in range(6)
        ]
        explore_posts = [
            create_post(
                content="What about this?",
                agent_id=f"a{i}",
            )
            for i in range(6)
        ]

        # Two debate signals
        observer.detect_phase(debate_posts)
        observer.detect_phase(debate_posts)
        # Interrupted by explore signal (or ambiguous)
        observer.detect_phase(explore_posts)
        # One more debate signal — not enough to transition
        signal = observer.detect_phase(debate_posts)
        assert signal.current_phase == Phase.EXPLORE


class TestConfidence:
    def test_high_confidence_when_stable(self, observer):
        posts = [create_post(content="What about this?", agent_id=f"a{i}") for i in range(5)]
        signal = observer.detect_phase(posts)
        assert signal.confidence >= 0.8

    def test_lower_confidence_during_pending_transition(self, observer):
        citation = Citation(
            document_id="D1", title="P", excerpt="E", relevance=0.9
        )
        debate_posts = [
            create_post(
                stance=AgentStance.CRITICAL,
                citations=[citation, citation],
                agent_id=f"a{i}",
            )
            for i in range(6)
        ]
        # First signal starts pending
        observer.detect_phase(debate_posts)
        signal = observer.detect_phase(debate_posts)
        assert signal.confidence < 0.9


class TestConfigurableAgentCount:
    def test_custom_num_agents(self, energy_calculator, observer_config):
        obs = ObserverAgent(
            energy_calculator=energy_calculator,
            config=observer_config,
            num_agents=4,
        )
        posts = [
            create_post(agent_id="a"),
            create_post(agent_id="b"),
            create_post(agent_id="c"),
            create_post(agent_id="d"),
        ]
        metrics = obs.calculate_metrics(posts)
        assert metrics.topic_diversity == pytest.approx(1.0, abs=0.01)

    def test_default_six_agents(self, observer):
        posts = [create_post(agent_id=f"a{i}") for i in range(3)]
        metrics = observer.calculate_metrics(posts)
        assert metrics.topic_diversity == pytest.approx(3 / 6, abs=0.01)


class TestMetaObservations:
    def test_stagnation_observation(self, observer):
        posts = [create_post(novelty_score=0.1) for _ in range(15)]
        signal = observer.detect_phase(posts)
        assert signal.observation is not None
        assert "circling" in signal.observation

    def test_high_disagreement_observation(self, observer):
        posts = [
            create_post(stance=AgentStance.CRITICAL, agent_id=f"a{i}")
            for i in range(8)
        ]
        signal = observer.detect_phase(posts)
        assert signal.observation is not None
        assert "disagreement" in signal.observation
