"""SQLAlchemy ORM table definitions matching Pydantic models."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _uuid() -> str:
    return str(uuid.uuid4())


class DBSession(Base):
    """deliberation_sessions table."""

    __tablename__ = "deliberation_sessions"

    id = Column(String(36), primary_key=True, default=_uuid)
    hypothesis = Column(Text, nullable=False)
    status = Column(String(20), nullable=False, default="pending")
    current_phase = Column(String(20), nullable=False, default="explore")
    config = Column(JSON, nullable=False, default=dict)
    # Platform additions (nullable for backward compatibility)
    subreddit_id = Column(String(36), ForeignKey("subreddits.id"), nullable=True)
    created_by = Column(String(36), nullable=True)
    estimated_cost_usd = Column(Float, default=0.0)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow)

    # Relationships
    posts = relationship("DBPost", back_populates="session", cascade="all, delete-orphan")
    energy_entries = relationship("DBEnergyHistory", back_populates="session", cascade="all, delete-orphan")
    consensus = relationship("DBConsensusMap", back_populates="session", uselist=False, cascade="all, delete-orphan")
    subreddit = relationship("DBSubreddit", back_populates="threads")
    synthesis = relationship("DBSynthesis", back_populates="session", uselist=False, cascade="all, delete-orphan")


class DBPost(Base):
    """posts table."""

    __tablename__ = "posts"
    __table_args__ = (
        Index("idx_posts_session", "session_id"),
        Index("idx_posts_agent", "agent_id"),
        Index("idx_posts_phase", "phase"),
    )

    id = Column(String(36), primary_key=True, default=_uuid)
    session_id = Column(String(36), ForeignKey("deliberation_sessions.id"), nullable=False)
    agent_id = Column(String(50), nullable=False)
    content = Column(Text, nullable=False)
    stance = Column(String(20), nullable=False)
    citations = Column(JSON, nullable=False, default=list)
    key_claims = Column(JSON, nullable=False, default=list)
    questions_raised = Column(JSON, nullable=False, default=list)
    connections_identified = Column(JSON, nullable=False, default=list)
    novelty_score = Column(Float, nullable=False, default=0.0)
    phase = Column(String(20), nullable=False)
    triggered_by = Column(JSON, nullable=False, default=list)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)

    session = relationship("DBSession", back_populates="posts")


class DBEnergyHistory(Base):
    """energy_history table."""

    __tablename__ = "energy_history"
    __table_args__ = (
        Index("idx_energy_session", "session_id"),
    )

    id = Column(String(36), primary_key=True, default=_uuid)
    session_id = Column(String(36), ForeignKey("deliberation_sessions.id"), nullable=False)
    turn = Column(Integer, nullable=False)
    energy = Column(Float, nullable=False)
    novelty = Column(Float)
    disagreement = Column(Float)
    questions = Column(Float)
    staleness = Column(Float)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)

    session = relationship("DBSession", back_populates="energy_entries")


class DBConsensusMap(Base):
    """consensus_maps table."""

    __tablename__ = "consensus_maps"
    __table_args__ = (
        UniqueConstraint("session_id", name="uq_consensus_session"),
    )

    id = Column(String(36), primary_key=True, default=_uuid)
    session_id = Column(String(36), ForeignKey("deliberation_sessions.id"), nullable=False)
    summary = Column(Text, nullable=False)
    agreements = Column(JSON, nullable=False, default=list)
    disagreements = Column(JSON, nullable=False, default=list)
    minority_positions = Column(JSON, nullable=False, default=list)
    serendipity_connections = Column(JSON, nullable=False, default=list)
    final_stances = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)

    session = relationship("DBSession", back_populates="consensus")


# ---------------------------------------------------------------------------
# Platform tables
# ---------------------------------------------------------------------------


class DBSubreddit(Base):
    """subreddits table."""

    __tablename__ = "subreddits"

    id = Column(String(36), primary_key=True, default=_uuid)
    name = Column(String(100), unique=True, nullable=False)
    display_name = Column(String(200), nullable=False)
    description = Column(Text, nullable=False, default="")
    purpose = Column(JSON, nullable=False, default=dict)
    output_template = Column(JSON, nullable=False, default=dict)
    participation_model = Column(String(20), nullable=False, default="guided")
    engine_overrides = Column(JSON, nullable=True)
    tool_configs = Column(JSON, nullable=False, default=list)
    min_agents = Column(Integer, nullable=False, default=3)
    max_agents = Column(Integer, nullable=False, default=8)
    always_include_red_team = Column(Boolean, nullable=False, default=True)
    max_cost_per_thread_usd = Column(Float, default=5.0)
    monthly_budget_usd = Column(Float, nullable=True)
    created_by = Column(String(36), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow)

    # Relationships
    threads = relationship("DBSession", back_populates="subreddit")
    memberships = relationship("DBSubredditMembership", back_populates="subreddit", cascade="all, delete-orphan")


class DBAgentIdentity(Base):
    """agent_identities table — persistent agents in the global pool."""

    __tablename__ = "agent_identities"
    __table_args__ = (
        Index("idx_agent_type", "agent_type"),
    )

    id = Column(String(36), primary_key=True, default=_uuid)
    agent_type = Column(String(100), unique=True, nullable=False)
    display_name = Column(String(200), nullable=False)
    expertise_tags = Column(JSON, nullable=False, default=list)
    persona_prompt = Column(Text, nullable=False)
    phase_mandates = Column(JSON, nullable=False, default=dict)
    domain_keywords = Column(JSON, nullable=False, default=list)
    knowledge_scope = Column(JSON, nullable=False, default=list)
    evaluation_criteria = Column(JSON, nullable=False, default=dict)
    is_red_team = Column(Boolean, nullable=False, default=False)
    status = Column(String(20), nullable=False, default="active")
    version = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)

    # Relationships
    memberships = relationship("DBSubredditMembership", back_populates="agent")


class DBSubredditMembership(Base):
    """subreddit_memberships table — agent's scoped role in a subreddit."""

    __tablename__ = "subreddit_memberships"
    __table_args__ = (
        UniqueConstraint("agent_id", "subreddit_id", name="uq_agent_subreddit"),
        Index("idx_membership_subreddit", "subreddit_id"),
        Index("idx_membership_agent", "agent_id"),
    )

    id = Column(String(36), primary_key=True, default=_uuid)
    agent_id = Column(String(36), ForeignKey("agent_identities.id"), nullable=False)
    subreddit_id = Column(String(36), ForeignKey("subreddits.id"), nullable=False)
    role = Column(String(20), nullable=False, default="member")
    role_prompt = Column(Text, nullable=False, default="")
    tool_access = Column(JSON, nullable=False, default=list)
    threads_participated = Column(Integer, nullable=False, default=0)
    total_posts = Column(Integer, nullable=False, default=0)
    joined_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)

    # Relationships
    agent = relationship("DBAgentIdentity", back_populates="memberships")
    subreddit = relationship("DBSubreddit", back_populates="memberships")


class DBSynthesis(Base):
    """syntheses table — structured output from deliberations."""

    __tablename__ = "syntheses"
    __table_args__ = (
        UniqueConstraint("session_id", name="uq_synthesis_session"),
    )

    id = Column(String(36), primary_key=True, default=_uuid)
    session_id = Column(String(36), ForeignKey("deliberation_sessions.id"), nullable=False)
    template_type = Column(String(50), nullable=False)
    sections = Column(JSON, nullable=False, default=dict)
    metadata_json = Column(JSON, nullable=False, default=dict)
    audit_chains = Column(JSON, nullable=False, default=list)
    total_citations = Column(Integer, nullable=False, default=0)
    citation_verification = Column(JSON, nullable=False, default=dict)
    tokens_used = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)

    session = relationship("DBSession", back_populates="synthesis")


class DBSynthesisMemory(Base):
    """synthesis_memories table — institutional memory for RAG."""

    __tablename__ = "synthesis_memories"
    __table_args__ = (
        Index("idx_synmem_subreddit", "subreddit_id"),
        Index("idx_synmem_thread", "thread_id"),
    )

    id = Column(String(36), primary_key=True, default=_uuid)
    thread_id = Column(String(36), nullable=False)
    subreddit_id = Column(String(36), nullable=False)
    subreddit_name = Column(String(100), nullable=False)
    topic = Column(Text, nullable=False)
    synthesis_content = Column(Text, nullable=False, default="")
    key_conclusions = Column(JSON, nullable=False, default=list)
    citations_used = Column(JSON, nullable=False, default=list)
    agents_involved = Column(JSON, nullable=False, default=list)
    template_type = Column(String(50), nullable=False, default="")
    confidence_level = Column(String(50), nullable=False, default="")
    evidence_quality = Column(String(50), nullable=False, default="")
    # Stored as JSON list of floats. Will become vector(1536) when pgvector is enabled.
    embedding = Column(JSON, nullable=False, default=list)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)


class DBMemoryAnnotation(Base):
    """memory_annotations table — human corrections to memories."""

    __tablename__ = "memory_annotations"
    __table_args__ = (
        Index("idx_annotation_memory", "memory_id"),
    )

    id = Column(String(36), primary_key=True, default=_uuid)
    memory_id = Column(String(36), ForeignKey("synthesis_memories.id"), nullable=False)
    annotation_type = Column(String(20), nullable=False)  # outdated, correction, confirmed, context
    content = Column(Text, nullable=False)
    created_by = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)


class DBCostRecord(Base):
    """cost_records table — per-call token usage tracking."""

    __tablename__ = "cost_records"
    __table_args__ = (
        Index("idx_cost_session", "session_id"),
    )

    id = Column(String(36), primary_key=True, default=_uuid)
    session_id = Column(String(36), ForeignKey("deliberation_sessions.id"), nullable=False)
    input_tokens = Column(Integer, nullable=False, default=0)
    output_tokens = Column(Integer, nullable=False, default=0)
    model = Column(String(100), nullable=False, default="default")
    estimated_cost_usd = Column(Float, nullable=False, default=0.0)
    recorded_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)
