"""Repository pattern for database operations."""

import logging
from typing import Dict, List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from colloquip.db.tables import DBConsensusMap, DBEnergyHistory, DBPost, DBSession
from colloquip.models import (
    AgentStance,
    ConsensusMap,
    DeliberationSession,
    EnergyUpdate,
    Phase,
    Post,
    SessionStatus,
)

logger = logging.getLogger(__name__)


class SessionRepository:
    """Abstracts all database read/write for deliberation data."""

    def __init__(self, session: AsyncSession):
        self.db = session

    # ---- Sessions ----

    async def save_session(self, session: DeliberationSession) -> None:
        """Insert or update a deliberation session."""
        db_session = await self.db.get(DBSession, str(session.id))
        if db_session:
            db_session.hypothesis = session.hypothesis
            db_session.status = session.status.value
            db_session.current_phase = session.phase.value
            db_session.config = session.config
            db_session.updated_at = session.updated_at
        else:
            db_session = DBSession(
                id=str(session.id),
                hypothesis=session.hypothesis,
                status=session.status.value,
                current_phase=session.phase.value,
                config=session.config,
                created_at=session.created_at,
                updated_at=session.updated_at,
            )
            self.db.add(db_session)
        await self.db.flush()

    async def get_session(self, session_id: UUID) -> Optional[DeliberationSession]:
        """Load a session by ID."""
        row = await self.db.get(DBSession, str(session_id))
        if not row:
            return None
        return _row_to_session(row)

    async def list_sessions(self, limit: int = 50, offset: int = 0) -> List[DeliberationSession]:
        """List sessions ordered by creation time (newest first)."""
        stmt = (
            select(DBSession)
            .order_by(DBSession.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.db.execute(stmt)
        rows = result.scalars().all()
        return [_row_to_session(r) for r in rows]

    async def update_session_status(self, session_id: UUID, status: SessionStatus, phase: Phase) -> None:
        """Update just the status and phase of a session."""
        row = await self.db.get(DBSession, str(session_id))
        if row:
            row.status = status.value
            row.current_phase = phase.value
            await self.db.flush()

    # ---- Posts ----

    async def save_post(self, post: Post) -> None:
        """Insert a single post."""
        db_post = DBPost(
            id=str(post.id),
            session_id=str(post.session_id),
            agent_id=post.agent_id,
            content=post.content,
            stance=post.stance.value,
            citations=[c.model_dump() for c in post.citations],
            key_claims=post.key_claims,
            questions_raised=post.questions_raised,
            connections_identified=post.connections_identified,
            novelty_score=post.novelty_score,
            phase=post.phase.value,
            triggered_by=post.triggered_by,
            created_at=post.created_at,
        )
        self.db.add(db_post)
        await self.db.flush()

    async def save_posts(self, posts: List[Post]) -> None:
        """Bulk insert posts."""
        for post in posts:
            await self.save_post(post)

    async def get_posts(self, session_id: UUID) -> List[Post]:
        """Load all posts for a session, ordered by creation time."""
        stmt = (
            select(DBPost)
            .where(DBPost.session_id == str(session_id))
            .order_by(DBPost.created_at)
        )
        result = await self.db.execute(stmt)
        rows = result.scalars().all()
        return [_row_to_post(r) for r in rows]

    # ---- Energy History ----

    async def save_energy_update(self, session_id: UUID, update: EnergyUpdate) -> None:
        """Insert an energy history entry."""
        entry = DBEnergyHistory(
            session_id=str(session_id),
            turn=update.turn,
            energy=update.energy,
            novelty=update.components.get("novelty"),
            disagreement=update.components.get("disagreement"),
            questions=update.components.get("questions"),
            staleness=update.components.get("staleness"),
        )
        self.db.add(entry)
        await self.db.flush()

    async def get_energy_history(self, session_id: UUID) -> List[EnergyUpdate]:
        """Load energy history for a session."""
        stmt = (
            select(DBEnergyHistory)
            .where(DBEnergyHistory.session_id == str(session_id))
            .order_by(DBEnergyHistory.turn)
        )
        result = await self.db.execute(stmt)
        rows = result.scalars().all()
        return [
            EnergyUpdate(
                turn=r.turn,
                energy=r.energy,
                components={
                    "novelty": r.novelty or 0.0,
                    "disagreement": r.disagreement or 0.0,
                    "questions": r.questions or 0.0,
                    "staleness": r.staleness or 0.0,
                },
            )
            for r in rows
        ]

    # ---- Consensus ----

    async def save_consensus(self, consensus: ConsensusMap) -> None:
        """Insert or replace the consensus map for a session."""
        existing = await self.db.execute(
            select(DBConsensusMap).where(
                DBConsensusMap.session_id == str(consensus.session_id)
            )
        )
        row = existing.scalar_one_or_none()
        if row:
            row.summary = consensus.summary
            row.agreements = consensus.agreements
            row.disagreements = consensus.disagreements
            row.minority_positions = consensus.minority_positions
            row.serendipity_connections = consensus.serendipity_connections
            row.final_stances = {k: v.value for k, v in consensus.final_stances.items()}
        else:
            db_consensus = DBConsensusMap(
                session_id=str(consensus.session_id),
                summary=consensus.summary,
                agreements=consensus.agreements,
                disagreements=consensus.disagreements,
                minority_positions=consensus.minority_positions,
                serendipity_connections=consensus.serendipity_connections,
                final_stances={k: v.value for k, v in consensus.final_stances.items()},
                created_at=consensus.created_at,
            )
            self.db.add(db_consensus)
        await self.db.flush()

    async def get_consensus(self, session_id: UUID) -> Optional[ConsensusMap]:
        """Load the consensus map for a session."""
        stmt = select(DBConsensusMap).where(
            DBConsensusMap.session_id == str(session_id)
        )
        result = await self.db.execute(stmt)
        row = result.scalar_one_or_none()
        if not row:
            return None
        return _row_to_consensus(row)

    # ---- Commit ----

    async def commit(self) -> None:
        """Commit the current transaction."""
        await self.db.commit()


# ---- Row-to-Pydantic converters ----

def _row_to_session(row: DBSession) -> DeliberationSession:
    return DeliberationSession(
        id=UUID(row.id),
        hypothesis=row.hypothesis,
        status=SessionStatus(row.status),
        phase=Phase(row.current_phase),
        config=row.config or {},
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _row_to_post(row: DBPost) -> Post:
    return Post(
        id=UUID(row.id),
        session_id=UUID(row.session_id),
        agent_id=row.agent_id,
        content=row.content,
        stance=AgentStance(row.stance),
        citations=row.citations or [],
        key_claims=row.key_claims or [],
        questions_raised=row.questions_raised or [],
        connections_identified=row.connections_identified or [],
        novelty_score=row.novelty_score,
        phase=Phase(row.phase),
        triggered_by=row.triggered_by or [],
        created_at=row.created_at,
    )


def _row_to_consensus(row: DBConsensusMap) -> ConsensusMap:
    stances = row.final_stances or {}
    return ConsensusMap(
        session_id=UUID(row.session_id),
        summary=row.summary,
        agreements=row.agreements or [],
        disagreements=row.disagreements or [],
        minority_positions=row.minority_positions or [],
        serendipity_connections=row.serendipity_connections or [],
        final_stances={k: AgentStance(v) for k, v in stances.items()},
        created_at=row.created_at,
    )
