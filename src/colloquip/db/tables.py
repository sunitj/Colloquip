"""SQLAlchemy ORM table definitions matching Pydantic models."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
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
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow)

    # Relationships
    posts = relationship("DBPost", back_populates="session", cascade="all, delete-orphan")
    energy_entries = relationship("DBEnergyHistory", back_populates="session", cascade="all, delete-orphan")
    consensus = relationship("DBConsensusMap", back_populates="session", uselist=False, cascade="all, delete-orphan")


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
