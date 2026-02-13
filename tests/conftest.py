"""Shared test fixtures and factory functions."""

from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID, uuid4

import pytest

from colloquip.config import EnergyConfig, ObserverConfig, TriggerConfig
from colloquip.energy import EnergyCalculator
from colloquip.models import (
    AgentConfig,
    AgentStance,
    Citation,
    ConversationMetrics,
    DeliberationSession,
    Phase,
    Post,
)
from colloquip.observer import ObserverAgent

# --- Factory functions ---

TEST_SESSION_ID = uuid4()


def create_post(
    agent_id: str = "biology",
    content: str = "Test post content.",
    stance: AgentStance = AgentStance.NEUTRAL,
    novelty_score: float = 0.5,
    phase: Phase = Phase.EXPLORE,
    citations: Optional[List[Citation]] = None,
    key_claims: Optional[List[str]] = None,
    questions_raised: Optional[List[str]] = None,
    connections_identified: Optional[List[str]] = None,
    triggered_by: Optional[List[str]] = None,
    session_id: Optional[UUID] = None,
) -> Post:
    """Create a test post with sensible defaults."""
    return Post(
        id=uuid4(),
        session_id=session_id or TEST_SESSION_ID,
        agent_id=agent_id,
        content=content,
        stance=stance,
        novelty_score=novelty_score,
        phase=phase,
        citations=citations or [],
        key_claims=key_claims or [],
        questions_raised=questions_raised or [],
        connections_identified=connections_identified or [],
        triggered_by=triggered_by or [],
        created_at=datetime.now(timezone.utc),
    )


def create_session(
    hypothesis: str = "GLP-1 agonists improve cognitive function",
) -> DeliberationSession:
    """Create a test session."""
    return DeliberationSession(hypothesis=hypothesis)


def create_agent_config(
    agent_id: str = "biology",
    display_name: str = "Biology & Target ID",
    domain_keywords: Optional[List[str]] = None,
    is_red_team: bool = False,
) -> AgentConfig:
    """Create a test agent config."""
    return AgentConfig(
        agent_id=agent_id,
        display_name=display_name,
        persona_prompt=f"You are the {display_name} expert.",
        phase_mandates={},
        domain_keywords=domain_keywords or ["mechanism", "target", "pathway", "receptor"],
        knowledge_scope=["biology", "preclinical"],
        is_red_team=is_red_team,
    )


def create_metrics(
    question_rate: float = 0.2,
    disagreement_rate: float = 0.2,
    topic_diversity: float = 0.5,
    citation_density: float = 0.3,
    novelty_avg: float = 0.5,
    energy: float = 0.6,
    posts_since_novel: int = 2,
) -> ConversationMetrics:
    """Create test metrics."""
    return ConversationMetrics(
        question_rate=question_rate,
        disagreement_rate=disagreement_rate,
        topic_diversity=topic_diversity,
        citation_density=citation_density,
        novelty_avg=novelty_avg,
        energy=energy,
        posts_since_novel=posts_since_novel,
    )


# --- Shared fixtures ---


@pytest.fixture
def energy_config():
    return EnergyConfig()


@pytest.fixture
def energy_calculator(energy_config):
    return EnergyCalculator(config=energy_config)


@pytest.fixture
def observer_config():
    return ObserverConfig()


@pytest.fixture
def observer(energy_calculator, observer_config):
    return ObserverAgent(energy_calculator=energy_calculator, config=observer_config)


@pytest.fixture
def trigger_config():
    return TriggerConfig()


@pytest.fixture
def session():
    return create_session()
