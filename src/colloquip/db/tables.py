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
    energy_entries = relationship(
        "DBEnergyHistory",
        back_populates="session",
        cascade="all, delete-orphan",
    )
    consensus = relationship(
        "DBConsensusMap",
        back_populates="session",
        uselist=False,
        cascade="all, delete-orphan",
    )
    subreddit = relationship("DBSubreddit", back_populates="threads")
    synthesis = relationship(
        "DBSynthesis",
        back_populates="session",
        uselist=False,
        cascade="all, delete-orphan",
    )


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
    tool_invocations = Column(JSON, nullable=False, default=list)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)

    session = relationship("DBSession", back_populates="posts")


class DBEnergyHistory(Base):
    """energy_history table."""

    __tablename__ = "energy_history"
    __table_args__ = (Index("idx_energy_session", "session_id"),)

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
    __table_args__ = (UniqueConstraint("session_id", name="uq_consensus_session"),)

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
    # Research program: human-authored markdown steering agent behavior
    research_program = Column(Text, nullable=True)
    research_program_version = Column(Integer, nullable=False, default=0)
    created_by = Column(String(36), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow)

    # Relationships
    threads = relationship("DBSession", back_populates="subreddit")
    memberships = relationship(
        "DBSubredditMembership",
        back_populates="subreddit",
        cascade="all, delete-orphan",
    )


class DBAgentIdentity(Base):
    """agent_identities table — persistent agents in the global pool."""

    __tablename__ = "agent_identities"
    __table_args__ = (Index("idx_agent_type", "agent_type"),)

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
    __table_args__ = (UniqueConstraint("session_id", name="uq_synthesis_session"),)

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
    # Bayesian confidence (Beta distribution parameters)
    confidence_alpha = Column(Float, nullable=False, default=2.0)
    confidence_beta = Column(Float, nullable=False, default=1.0)
    # Stored as JSON list of floats. Will become vector(1536) when pgvector is enabled.
    embedding = Column(JSON, nullable=False, default=list)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)


class DBMemoryAnnotation(Base):
    """memory_annotations table — human corrections to memories."""

    __tablename__ = "memory_annotations"
    __table_args__ = (Index("idx_annotation_memory", "memory_id"),)

    id = Column(String(36), primary_key=True, default=_uuid)
    memory_id = Column(String(36), ForeignKey("synthesis_memories.id"), nullable=False)
    annotation_type = Column(String(20), nullable=False)  # outdated, correction, confirmed, context
    content = Column(Text, nullable=False)
    created_by = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)


class DBCostRecord(Base):
    """cost_records table — per-call token usage tracking."""

    __tablename__ = "cost_records"
    __table_args__ = (Index("idx_cost_session", "session_id"),)

    id = Column(String(36), primary_key=True, default=_uuid)
    session_id = Column(String(36), ForeignKey("deliberation_sessions.id"), nullable=False)
    input_tokens = Column(Integer, nullable=False, default=0)
    output_tokens = Column(Integer, nullable=False, default=0)
    model = Column(String(100), nullable=False, default="default")
    estimated_cost_usd = Column(Float, nullable=False, default=0.0)
    recorded_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)


# ---------------------------------------------------------------------------
# Phase 4: Event-Driven Trigger tables
# ---------------------------------------------------------------------------


class DBWatcher(Base):
    """watchers table — event monitoring configurations."""

    __tablename__ = "watchers"
    __table_args__ = (Index("idx_watcher_subreddit", "subreddit_id"),)

    id = Column(String(36), primary_key=True, default=_uuid)
    watcher_type = Column(String(20), nullable=False)  # literature, scheduled, webhook
    subreddit_id = Column(String(36), ForeignKey("subreddits.id"), nullable=False)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=False, default="")
    query = Column(Text, nullable=False, default="")
    poll_interval_seconds = Column(Integer, nullable=False, default=300)
    enabled = Column(Boolean, nullable=False, default=True)
    config = Column(JSON, nullable=False, default=dict)
    auto_create_thread = Column(Boolean, nullable=False, default=False)
    auto_thread_approval_rate = Column(Float, nullable=True)
    created_by = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow)

    # Relationships
    events = relationship("DBWatcherEvent", back_populates="watcher", cascade="all, delete-orphan")
    notifications = relationship(
        "DBNotification",
        back_populates="watcher",
        cascade="all, delete-orphan",
    )


class DBWatcherEvent(Base):
    """watcher_events table — events detected by watchers."""

    __tablename__ = "watcher_events"
    __table_args__ = (
        Index("idx_event_watcher", "watcher_id"),
        Index("idx_event_subreddit", "subreddit_id"),
    )

    id = Column(String(36), primary_key=True, default=_uuid)
    watcher_id = Column(String(36), ForeignKey("watchers.id"), nullable=False)
    subreddit_id = Column(String(36), nullable=False)
    title = Column(Text, nullable=False)
    summary = Column(Text, nullable=False, default="")
    source_type = Column(String(50), nullable=False, default="")
    source_id = Column(String(200), nullable=False, default="")
    source_url = Column(Text, nullable=True)
    source_metadata = Column(JSON, nullable=False, default=dict)
    raw_data = Column(JSON, nullable=False, default=dict)
    triage_signal = Column(String(20), nullable=True)  # low, medium, high
    triage_reasoning = Column(Text, nullable=True)
    detected_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)

    watcher = relationship("DBWatcher", back_populates="events")


class DBNotification(Base):
    """notifications table — user-facing notifications from triage."""

    __tablename__ = "notifications"
    __table_args__ = (
        Index("idx_notification_subreddit", "subreddit_id"),
        Index("idx_notification_status", "status"),
    )

    id = Column(String(36), primary_key=True, default=_uuid)
    watcher_id = Column(String(36), ForeignKey("watchers.id"), nullable=False)
    event_id = Column(String(36), nullable=False)
    subreddit_id = Column(String(36), nullable=False)
    title = Column(Text, nullable=False)
    summary = Column(Text, nullable=False, default="")
    signal = Column(String(20), nullable=False)  # low, medium, high
    suggested_hypothesis = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, default="pending")
    action_taken = Column(String(20), nullable=True)
    thread_id = Column(String(36), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)
    acted_at = Column(DateTime(timezone=True), nullable=True)

    watcher = relationship("DBWatcher", back_populates="notifications")


# ---------------------------------------------------------------------------
# Phase 5: Cross-Subreddit + Feedback tables
# ---------------------------------------------------------------------------


class DBCrossReference(Base):
    """cross_references table — detected links between subreddit memories."""

    __tablename__ = "cross_references"
    __table_args__ = (
        Index("idx_crossref_source", "source_memory_id"),
        Index("idx_crossref_target", "target_memory_id"),
    )

    id = Column(String(36), primary_key=True, default=_uuid)
    source_memory_id = Column(String(36), ForeignKey("synthesis_memories.id"), nullable=False)
    target_memory_id = Column(String(36), ForeignKey("synthesis_memories.id"), nullable=False)
    source_subreddit_id = Column(String(36), nullable=False)
    target_subreddit_id = Column(String(36), nullable=False)
    source_subreddit_name = Column(String(100), nullable=False, default="")
    target_subreddit_name = Column(String(100), nullable=False, default="")
    similarity = Column(Float, nullable=False, default=0.0)
    shared_entities = Column(JSON, nullable=False, default=list)
    reasoning = Column(Text, nullable=False, default="")
    status = Column(String(20), nullable=False, default="pending")  # pending, confirmed, dismissed
    reviewed_by = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)


class DBOutcomeReport(Base):
    """outcome_reports table — real-world outcome tracking."""

    __tablename__ = "outcome_reports"
    __table_args__ = (
        Index("idx_outcome_thread", "thread_id"),
        Index("idx_outcome_subreddit", "subreddit_id"),
    )

    id = Column(String(36), primary_key=True, default=_uuid)
    thread_id = Column(String(36), nullable=False)
    subreddit_id = Column(String(36), nullable=False)
    # confirmed, partially_confirmed, contradicted, inconclusive
    outcome_type = Column(String(30), nullable=False)
    summary = Column(Text, nullable=False)
    evidence = Column(Text, nullable=False, default="")
    conclusions_evaluated = Column(JSON, nullable=False, default=list)
    agent_assessments = Column(JSON, nullable=False, default=dict)
    reported_by = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)


# ---------------------------------------------------------------------------
# Phase 6: Jobs, Pipelines, and Agent Tool Integration
# ---------------------------------------------------------------------------


class DBNextflowProcess(Base):
    """nextflow_processes table — catalog of pre-built NF processes."""

    __tablename__ = "nextflow_processes"
    __table_args__ = (Index("idx_nfproc_category", "category"),)

    id = Column(String(36), primary_key=True, default=_uuid)
    process_id = Column(String(100), unique=True, nullable=False)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=False, default="")
    category = Column(String(100), nullable=False, default="")
    input_channels = Column(JSON, nullable=False, default=list)
    output_channels = Column(JSON, nullable=False, default=list)
    parameters = Column(JSON, nullable=False, default=list)
    container = Column(String(500), nullable=False, default="")
    resource_requirements = Column(JSON, nullable=False, default=dict)
    version = Column(String(50), nullable=False, default="1.0.0")
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow)


class DBJob(Base):
    """jobs table — computational job execution tracking."""

    __tablename__ = "jobs"
    __table_args__ = (
        Index("idx_job_session", "session_id"),
        Index("idx_job_status", "status"),
        Index("idx_job_thread", "thread_id"),
    )

    id = Column(String(36), primary_key=True, default=_uuid)
    session_id = Column(String(36), ForeignKey("deliberation_sessions.id"), nullable=False)
    thread_id = Column(String(36), nullable=True)
    agent_id = Column(String(50), nullable=False)
    pipeline = Column(JSON, nullable=False, default=dict)
    compute_backend = Column(String(20), nullable=False, default="local")
    compute_profile = Column(String(100), nullable=False, default="standard")
    status = Column(String(20), nullable=False, default="pending")
    nextflow_run_id = Column(String(200), nullable=True)
    result_summary = Column(Text, nullable=True)
    result_artifacts = Column(JSON, nullable=False, default=list)
    error_message = Column(Text, nullable=True)
    submitted_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)

    session = relationship("DBSession")


class DBActionProposal(Base):
    """action_proposals table — agent proposals requiring human approval."""

    __tablename__ = "action_proposals"
    __table_args__ = (
        Index("idx_proposal_session", "session_id"),
        Index("idx_proposal_status", "status"),
    )

    id = Column(String(36), primary_key=True, default=_uuid)
    session_id = Column(String(36), ForeignKey("deliberation_sessions.id"), nullable=False)
    thread_id = Column(String(36), nullable=True)
    agent_id = Column(String(50), nullable=False)
    action_type = Column(String(50), nullable=False, default="launch_pipeline")
    description = Column(Text, nullable=False, default="")
    rationale = Column(Text, nullable=False, default="")
    proposed_pipeline = Column(JSON, nullable=True)
    proposed_params = Column(JSON, nullable=False, default=dict)
    status = Column(String(20), nullable=False, default="pending")
    reviewed_by = Column(String(100), nullable=True)
    review_note = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)


# ---------------------------------------------------------------------------
# Phase 7: Autonomous Research Loop
# ---------------------------------------------------------------------------


class DBResearchJob(Base):
    """research_jobs table — autonomous research loop state."""

    __tablename__ = "research_jobs"
    __table_args__ = (
        Index("idx_rjob_subreddit", "subreddit_id"),
        Index("idx_rjob_status", "status"),
    )

    id = Column(String(36), primary_key=True, default=_uuid)
    subreddit_id = Column(String(36), ForeignKey("subreddits.id"), nullable=False)
    status = Column(String(20), nullable=False, default="pending")
    research_program_version = Column(Integer, nullable=False, default=0)

    # Loop state
    current_iteration = Column(Integer, nullable=False, default=0)
    max_iterations = Column(Integer, nullable=False, default=50)
    threads_completed = Column(JSON, nullable=False, default=list)
    threads_discarded = Column(JSON, nullable=False, default=list)

    # Evaluation
    baseline_metric = Column(Float, nullable=True)
    best_metric = Column(Float, nullable=True)
    metric_history = Column(JSON, nullable=False, default=list)

    # Budget
    total_cost_usd = Column(Float, nullable=False, default=0.0)
    max_cost_usd = Column(Float, nullable=False, default=25.0)
    max_threads_per_hour = Column(Integer, nullable=False, default=3)
    max_runtime_hours = Column(Float, nullable=False, default=24.0)

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow)
    started_at = Column(DateTime(timezone=True), nullable=True)

    subreddit = relationship("DBSubreddit")


class DBDataConnection(Base):
    """data_connections table — user-configured database connections."""

    __tablename__ = "data_connections"
    __table_args__ = (Index("idx_dataconn_subreddit", "subreddit_id"),)

    id = Column(String(36), primary_key=True, default=_uuid)
    subreddit_id = Column(String(36), ForeignKey("subreddits.id"), nullable=False)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=False, default="")
    db_type = Column(String(20), nullable=False, default="postgresql")
    connection_string = Column(Text, nullable=False, default="")
    read_only = Column(Boolean, nullable=False, default=True)
    enabled = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)
