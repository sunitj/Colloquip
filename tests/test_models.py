"""Tests for core data models."""

import json
from uuid import uuid4

import pytest
from pydantic import ValidationError

from colloquip.models import (
    AgentConfig,
    AgentStance,
    Citation,
    ConsensusMap,
    ConversationMetrics,
    DeliberationSession,
    EngineConfig,
    EnergySource,
    EnergyUpdate,
    HumanIntervention,
    Phase,
    PhaseSignal,
    Post,
    SessionStatus,
)

from tests.conftest import create_post, create_session, create_metrics


class TestPhaseEnum:
    def test_all_phases_exist(self):
        assert Phase.EXPLORE == "explore"
        assert Phase.DEBATE == "debate"
        assert Phase.DEEPEN == "deepen"
        assert Phase.CONVERGE == "converge"
        assert Phase.SYNTHESIS == "synthesis"

    def test_phase_from_string(self):
        assert Phase("explore") == Phase.EXPLORE


class TestAgentStance:
    def test_all_stances(self):
        assert len(AgentStance) == 4
        assert AgentStance.NOVEL_CONNECTION == "novel_connection"


class TestPost:
    def test_create_valid_post(self):
        post = create_post()
        assert post.agent_id == "biology"
        assert post.stance == AgentStance.NEUTRAL
        assert 0.0 <= post.novelty_score <= 1.0

    def test_novelty_score_clamped(self):
        with pytest.raises(ValidationError):
            create_post(novelty_score=1.5)

        with pytest.raises(ValidationError):
            create_post(novelty_score=-0.1)

    def test_serialization_roundtrip(self):
        post = create_post(
            content="Test content",
            stance=AgentStance.CRITICAL,
            novelty_score=0.8,
            key_claims=["claim1", "claim2"],
        )
        data = post.model_dump(mode="json")
        restored = Post.model_validate(data)
        assert restored.content == post.content
        assert restored.stance == post.stance
        assert restored.key_claims == post.key_claims

    def test_post_with_citations(self):
        citation = Citation(
            document_id="DOC-001",
            title="Test Paper",
            excerpt="Relevant excerpt",
            relevance=0.9,
        )
        post = create_post(citations=[citation])
        assert len(post.citations) == 1
        assert post.citations[0].title == "Test Paper"


class TestConversationMetrics:
    def test_valid_metrics(self):
        metrics = create_metrics()
        assert 0.0 <= metrics.energy <= 1.0

    def test_metrics_validation(self):
        with pytest.raises(ValidationError):
            ConversationMetrics(
                question_rate=1.5,  # Invalid: > 1.0
                disagreement_rate=0.2,
                topic_diversity=0.5,
                citation_density=0.3,
                novelty_avg=0.5,
                energy=0.6,
                posts_since_novel=2,
            )


class TestDeliberationSession:
    def test_create_session(self):
        session = create_session()
        assert session.status == SessionStatus.PENDING
        assert session.phase == Phase.EXPLORE

    def test_session_serialization(self):
        session = create_session()
        data = session.model_dump(mode="json")
        restored = DeliberationSession.model_validate(data)
        assert restored.hypothesis == session.hypothesis


class TestConsensusMap:
    def test_create_consensus_map(self):
        cm = ConsensusMap(
            session_id=uuid4(),
            summary="Test summary",
            agreements=["Agreement 1"],
            disagreements=["Disagreement 1"],
            final_stances={"biology": AgentStance.SUPPORTIVE},
        )
        assert cm.summary == "Test summary"
        assert len(cm.agreements) == 1


class TestEngineConfig:
    def test_defaults(self):
        config = EngineConfig()
        assert config.max_turns == 30
        assert config.min_posts == 12
        assert config.energy_threshold == 0.2
        assert config.low_energy_rounds == 3


class TestEnergySource:
    def test_all_sources(self):
        assert len(EnergySource) == 4
        assert EnergySource.HUMAN_INTERVENTION == "human_intervention"
