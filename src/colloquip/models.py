"""Core data models for the Colloquip deliberation system."""

from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class Phase(str, Enum):
    EXPLORE = "explore"
    DEBATE = "debate"
    DEEPEN = "deepen"
    CONVERGE = "converge"
    SYNTHESIS = "synthesis"


class AgentStance(str, Enum):
    SUPPORTIVE = "supportive"
    CRITICAL = "critical"
    NEUTRAL = "neutral"
    NOVEL_CONNECTION = "novel_connection"


class EnergySource(str, Enum):
    NEW_KNOWLEDGE = "new_knowledge"
    HUMAN_INTERVENTION = "human_intervention"
    NOVEL_POST = "novel_post"
    RED_TEAM_CHALLENGE = "red_team_challenge"


class SessionStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"


class Citation(BaseModel):
    document_id: str
    title: str
    excerpt: str
    relevance: float = Field(ge=0.0, le=1.0)


class Post(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    session_id: UUID
    agent_id: str
    content: str
    stance: AgentStance
    citations: List[Citation] = Field(default_factory=list)
    key_claims: List[str] = Field(default_factory=list)
    questions_raised: List[str] = Field(default_factory=list)
    connections_identified: List[str] = Field(default_factory=list)
    novelty_score: float = Field(default=0.0, ge=0.0, le=1.0)
    phase: Phase
    triggered_by: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ConversationMetrics(BaseModel):
    question_rate: float = Field(ge=0.0, le=1.0)
    disagreement_rate: float = Field(ge=0.0, le=1.0)
    topic_diversity: float = Field(ge=0.0, le=1.0)
    citation_density: float = Field(ge=0.0, le=1.0)
    novelty_avg: float = Field(ge=0.0, le=1.0)
    energy: float = Field(ge=0.0, le=1.0)
    posts_since_novel: int = Field(ge=0)


class PhaseSignal(BaseModel):
    current_phase: Phase
    confidence: float = Field(ge=0.0, le=1.0)
    metrics: ConversationMetrics
    observation: Optional[str] = None


class EnergyUpdate(BaseModel):
    turn: int
    energy: float = Field(ge=0.0, le=1.0)
    components: Dict[str, float] = Field(default_factory=dict)


class DeliberationSession(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    hypothesis: str
    status: SessionStatus = SessionStatus.PENDING
    phase: Phase = Phase.EXPLORE
    config: Dict = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ConsensusMap(BaseModel):
    session_id: UUID
    summary: str
    agreements: List[str] = Field(default_factory=list)
    disagreements: List[str] = Field(default_factory=list)
    minority_positions: List[str] = Field(default_factory=list)
    serendipity_connections: List[Dict] = Field(default_factory=list)
    final_stances: Dict[str, AgentStance] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AgentConfig(BaseModel):
    agent_id: str
    display_name: str
    persona_prompt: str
    phase_mandates: Dict[Phase, str]
    domain_keywords: List[str]
    knowledge_scope: List[str]
    evaluation_criteria: Dict[str, float] = Field(default_factory=dict)
    is_red_team: bool = False


class EngineConfig(BaseModel):
    max_turns: int = 30
    min_posts: int = 12
    energy_threshold: float = 0.2
    low_energy_rounds: int = 3
    refractory_period: int = 2
    hysteresis_threshold: int = 3


class HumanIntervention(BaseModel):
    session_id: UUID
    type: str  # question, data, redirect, terminate
    content: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AgentDependencies(BaseModel):
    """Context passed to an agent when generating a post."""
    session: DeliberationSession
    phase: Phase
    phase_signal: PhaseSignal
    posts: List[Post]
    knowledge_context: List[str] = Field(default_factory=list)

    model_config = {"arbitrary_types_allowed": True}
