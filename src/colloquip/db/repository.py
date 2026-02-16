"""Repository pattern for database operations."""

import logging
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from colloquip.db.tables import (
    DBAgentIdentity,
    DBConsensusMap,
    DBCostRecord,
    DBCrossReference,
    DBEnergyHistory,
    DBMemoryAnnotation,
    DBPost,
    DBSession,
    DBSubreddit,
    DBSubredditMembership,
    DBSynthesis,
    DBSynthesisMemory,
)
from colloquip.models import (
    AgentStance,
    AgentStatus,
    BaseAgentIdentity,
    ConsensusMap,
    DeliberationSession,
    EnergyUpdate,
    Phase,
    Post,
    SessionStatus,
    SubredditMembership,
    SubredditRole,
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
        stmt = select(DBSession).order_by(DBSession.created_at.desc()).limit(limit).offset(offset)
        result = await self.db.execute(stmt)
        rows = result.scalars().all()
        return [_row_to_session(r) for r in rows]

    async def update_session_status(
        self,
        session_id: UUID,
        status: SessionStatus,
        phase: Phase,
    ) -> None:
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
            select(DBPost).where(DBPost.session_id == str(session_id)).order_by(DBPost.created_at)
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
            select(DBConsensusMap).where(DBConsensusMap.session_id == str(consensus.session_id))
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
        stmt = select(DBConsensusMap).where(DBConsensusMap.session_id == str(session_id))
        result = await self.db.execute(stmt)
        row = result.scalar_one_or_none()
        if not row:
            return None
        return _row_to_consensus(row)

    # ---- Subreddits ----

    async def save_subreddit(
        self,
        subreddit_id: str,
        name: str,
        display_name: str,
        description: str = "",
        purpose: dict = None,
        output_template: dict = None,
        participation_model: str = "guided",
        tool_configs: list = None,
        min_agents: int = 3,
        max_agents: int = 8,
        always_include_red_team: bool = True,
        max_cost_per_thread_usd: float = 5.0,
        monthly_budget_usd: float = None,
        engine_overrides: dict = None,
        created_by: str = None,
    ) -> None:
        """Insert or update a subreddit."""
        row = await self.db.get(DBSubreddit, subreddit_id)
        if row:
            row.name = name
            row.display_name = display_name
            row.description = description
            row.purpose = purpose or {}
            row.output_template = output_template or {}
            row.participation_model = participation_model
            row.tool_configs = tool_configs or []
        else:
            row = DBSubreddit(
                id=subreddit_id,
                name=name,
                display_name=display_name,
                description=description,
                purpose=purpose or {},
                output_template=output_template or {},
                participation_model=participation_model,
                tool_configs=tool_configs or [],
                min_agents=min_agents,
                max_agents=max_agents,
                always_include_red_team=always_include_red_team,
                max_cost_per_thread_usd=max_cost_per_thread_usd,
                monthly_budget_usd=monthly_budget_usd,
                engine_overrides=engine_overrides,
                created_by=created_by,
            )
            self.db.add(row)
        await self.db.flush()

    async def get_subreddit(self, subreddit_id: str) -> Optional[dict]:
        """Load a subreddit by ID."""
        row = await self.db.get(DBSubreddit, subreddit_id)
        if not row:
            return None
        return _row_to_subreddit_dict(row)

    async def get_subreddit_by_name(self, name: str) -> Optional[dict]:
        """Load a subreddit by its unique name/slug."""
        stmt = select(DBSubreddit).where(DBSubreddit.name == name)
        result = await self.db.execute(stmt)
        row = result.scalar_one_or_none()
        if not row:
            return None
        return _row_to_subreddit_dict(row)

    async def list_subreddits(self, limit: int = 50) -> List[dict]:
        """List all subreddits."""
        stmt = select(DBSubreddit).order_by(DBSubreddit.created_at.desc()).limit(limit)
        result = await self.db.execute(stmt)
        return [_row_to_subreddit_dict(r) for r in result.scalars().all()]

    # ---- Agent Identities ----

    async def save_agent(self, agent: BaseAgentIdentity) -> None:
        """Insert or update an agent identity."""
        row = await self.db.get(DBAgentIdentity, str(agent.id))
        if row:
            row.display_name = agent.display_name
            row.expertise_tags = agent.expertise_tags
            row.persona_prompt = agent.persona_prompt
            row.phase_mandates = agent.phase_mandates
            row.domain_keywords = agent.domain_keywords
            row.knowledge_scope = agent.knowledge_scope
            row.evaluation_criteria = agent.evaluation_criteria
            row.is_red_team = agent.is_red_team
            row.status = agent.status.value
            row.version = agent.version
        else:
            row = DBAgentIdentity(
                id=str(agent.id),
                agent_type=agent.agent_type,
                display_name=agent.display_name,
                expertise_tags=agent.expertise_tags,
                persona_prompt=agent.persona_prompt,
                phase_mandates=agent.phase_mandates,
                domain_keywords=agent.domain_keywords,
                knowledge_scope=agent.knowledge_scope,
                evaluation_criteria=agent.evaluation_criteria,
                is_red_team=agent.is_red_team,
                status=agent.status.value,
                version=agent.version,
                created_at=agent.created_at,
            )
            self.db.add(row)
        await self.db.flush()

    async def get_agent(self, agent_id: str) -> Optional[BaseAgentIdentity]:
        """Load an agent by UUID string."""
        row = await self.db.get(DBAgentIdentity, agent_id)
        if not row:
            return None
        return _row_to_agent_identity(row)

    async def get_agent_by_type(self, agent_type: str) -> Optional[BaseAgentIdentity]:
        """Load an agent by agent_type."""
        stmt = select(DBAgentIdentity).where(DBAgentIdentity.agent_type == agent_type)
        result = await self.db.execute(stmt)
        row = result.scalar_one_or_none()
        if not row:
            return None
        return _row_to_agent_identity(row)

    async def list_agents(self, limit: int = 100) -> List[BaseAgentIdentity]:
        """List all agents in the pool."""
        stmt = select(DBAgentIdentity).order_by(DBAgentIdentity.created_at).limit(limit)
        result = await self.db.execute(stmt)
        return [_row_to_agent_identity(r) for r in result.scalars().all()]

    # ---- Memberships ----

    async def save_membership(self, membership: SubredditMembership) -> None:
        """Insert or update a subreddit membership."""
        row = await self.db.get(DBSubredditMembership, str(membership.id))
        if row:
            row.role = membership.role.value
            row.role_prompt = membership.role_prompt
            row.tool_access = membership.tool_access
        else:
            row = DBSubredditMembership(
                id=str(membership.id),
                agent_id=str(membership.agent_id),
                subreddit_id=str(membership.subreddit_id),
                role=membership.role.value,
                role_prompt=membership.role_prompt,
                tool_access=membership.tool_access,
                joined_at=membership.joined_at,
            )
            self.db.add(row)
        await self.db.flush()

    async def get_subreddit_members(self, subreddit_id: str) -> List[SubredditMembership]:
        """Get all members of a subreddit."""
        stmt = (
            select(DBSubredditMembership)
            .where(DBSubredditMembership.subreddit_id == subreddit_id)
            .order_by(DBSubredditMembership.joined_at)
        )
        result = await self.db.execute(stmt)
        return [_row_to_membership(r) for r in result.scalars().all()]

    async def get_agent_subreddits(self, agent_id: str) -> List[SubredditMembership]:
        """Get all subreddits an agent belongs to."""
        stmt = select(DBSubredditMembership).where(DBSubredditMembership.agent_id == agent_id)
        result = await self.db.execute(stmt)
        return [_row_to_membership(r) for r in result.scalars().all()]

    # ---- Synthesis ----

    async def save_synthesis(
        self,
        session_id: str,
        template_type: str,
        sections: dict,
        metadata: dict = None,
        audit_chains: list = None,
        total_citations: int = 0,
        citation_verification: dict = None,
        tokens_used: int = 0,
    ) -> None:
        """Save a synthesis for a session."""
        existing = await self.db.execute(
            select(DBSynthesis).where(DBSynthesis.session_id == session_id)
        )
        row = existing.scalar_one_or_none()
        if row:
            row.template_type = template_type
            row.sections = sections
            row.metadata_json = metadata or {}
            row.audit_chains = audit_chains or []
            row.total_citations = total_citations
            row.citation_verification = citation_verification or {}
            row.tokens_used = tokens_used
        else:
            row = DBSynthesis(
                session_id=session_id,
                template_type=template_type,
                sections=sections,
                metadata_json=metadata or {},
                audit_chains=audit_chains or [],
                total_citations=total_citations,
                citation_verification=citation_verification or {},
                tokens_used=tokens_used,
            )
            self.db.add(row)
        await self.db.flush()

    async def get_synthesis(self, session_id: str) -> Optional[dict]:
        """Load synthesis for a session."""
        stmt = select(DBSynthesis).where(DBSynthesis.session_id == session_id)
        result = await self.db.execute(stmt)
        row = result.scalar_one_or_none()
        if not row:
            return None
        return {
            "id": row.id,
            "session_id": row.session_id,
            "template_type": row.template_type,
            "sections": row.sections or {},
            "metadata": row.metadata_json or {},
            "audit_chains": row.audit_chains or [],
            "total_citations": row.total_citations,
            "citation_verification": row.citation_verification or {},
            "tokens_used": row.tokens_used,
            "created_at": row.created_at,
        }

    # ---- Cost Records ----

    async def save_cost_record(
        self,
        session_id: str,
        input_tokens: int,
        output_tokens: int,
        model: str = "default",
        estimated_cost_usd: float = 0.0,
    ) -> None:
        """Save a cost record."""
        row = DBCostRecord(
            session_id=session_id,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            model=model,
            estimated_cost_usd=estimated_cost_usd,
        )
        self.db.add(row)
        await self.db.flush()

    async def get_thread_costs(self, session_id: str) -> List[dict]:
        """Get all cost records for a session."""
        stmt = (
            select(DBCostRecord)
            .where(DBCostRecord.session_id == session_id)
            .order_by(DBCostRecord.recorded_at)
        )
        result = await self.db.execute(stmt)
        return [
            {
                "input_tokens": r.input_tokens,
                "output_tokens": r.output_tokens,
                "model": r.model,
                "estimated_cost_usd": r.estimated_cost_usd,
                "recorded_at": r.recorded_at,
            }
            for r in result.scalars().all()
        ]

    # ---- Synthesis Memories ----

    async def save_memory(self, memory: "SynthesisMemory") -> None:
        """Save a synthesis memory."""

        row = await self.db.get(DBSynthesisMemory, str(memory.id))
        if row:
            row.topic = memory.topic
            row.synthesis_content = memory.synthesis_content
            row.key_conclusions = memory.key_conclusions
            row.citations_used = memory.citations_used
            row.agents_involved = memory.agents_involved
            row.template_type = memory.template_type
            row.confidence_level = memory.confidence_level
            row.evidence_quality = memory.evidence_quality
            row.confidence_alpha = memory.confidence_alpha
            row.confidence_beta = memory.confidence_beta
            row.embedding = memory.embedding
        else:
            row = DBSynthesisMemory(
                id=str(memory.id),
                thread_id=str(memory.thread_id),
                subreddit_id=str(memory.subreddit_id),
                subreddit_name=memory.subreddit_name,
                topic=memory.topic,
                synthesis_content=memory.synthesis_content,
                key_conclusions=memory.key_conclusions,
                citations_used=memory.citations_used,
                agents_involved=memory.agents_involved,
                template_type=memory.template_type,
                confidence_level=memory.confidence_level,
                evidence_quality=memory.evidence_quality,
                confidence_alpha=memory.confidence_alpha,
                confidence_beta=memory.confidence_beta,
                embedding=memory.embedding,
                created_at=memory.created_at,
            )
            self.db.add(row)
        await self.db.flush()

    async def get_memory(self, memory_id: str) -> Optional[dict]:
        """Load a synthesis memory by ID."""
        row = await self.db.get(DBSynthesisMemory, memory_id)
        if not row:
            return None
        return _row_to_memory_dict(row)

    async def list_memories(self, subreddit_id: str = None, limit: int = 50) -> List[dict]:
        """List synthesis memories, optionally filtered by subreddit."""
        stmt = select(DBSynthesisMemory).order_by(DBSynthesisMemory.created_at.desc())
        if subreddit_id:
            stmt = stmt.where(DBSynthesisMemory.subreddit_id == subreddit_id)
        stmt = stmt.limit(limit)
        result = await self.db.execute(stmt)
        return [_row_to_memory_dict(r) for r in result.scalars().all()]

    async def save_annotation(
        self, memory_id: str, annotation_type: str, content: str, created_by: str = None
    ) -> str:
        """Save a memory annotation. Returns the annotation ID."""
        import uuid

        ann_id = str(uuid.uuid4())
        row = DBMemoryAnnotation(
            id=ann_id,
            memory_id=memory_id,
            annotation_type=annotation_type,
            content=content,
            created_by=created_by,
        )
        self.db.add(row)
        await self.db.flush()
        return ann_id

    async def get_annotations(self, memory_id: str) -> List[dict]:
        """Get all annotations for a memory."""
        stmt = (
            select(DBMemoryAnnotation)
            .where(DBMemoryAnnotation.memory_id == memory_id)
            .order_by(DBMemoryAnnotation.created_at)
        )
        result = await self.db.execute(stmt)
        return [
            {
                "id": r.id,
                "memory_id": r.memory_id,
                "annotation_type": r.annotation_type,
                "content": r.content,
                "created_by": r.created_by,
                "created_at": r.created_at,
            }
            for r in result.scalars().all()
        ]

    # ---- Cross-References ----

    async def save_cross_reference(
        self,
        cross_ref_id: str,
        source_memory_id: str,
        target_memory_id: str,
        source_subreddit_id: str,
        target_subreddit_id: str,
        source_subreddit_name: str = "",
        target_subreddit_name: str = "",
        similarity: float = 0.0,
        shared_entities: list = None,
        reasoning: str = "",
        status: str = "pending",
    ) -> None:
        """Save a cross-reference between two memories."""
        row = await self.db.get(DBCrossReference, cross_ref_id)
        if row:
            row.similarity = similarity
            row.shared_entities = shared_entities or []
            row.reasoning = reasoning
            row.status = status
        else:
            row = DBCrossReference(
                id=cross_ref_id,
                source_memory_id=source_memory_id,
                target_memory_id=target_memory_id,
                source_subreddit_id=source_subreddit_id,
                target_subreddit_id=target_subreddit_id,
                source_subreddit_name=source_subreddit_name,
                target_subreddit_name=target_subreddit_name,
                similarity=similarity,
                shared_entities=shared_entities or [],
                reasoning=reasoning,
                status=status,
            )
            self.db.add(row)
        await self.db.flush()

    async def list_cross_references(self, status: str = None) -> list[dict]:
        """List all cross-references, optionally filtered by status."""
        stmt = select(DBCrossReference).order_by(DBCrossReference.created_at.desc())
        if status:
            stmt = stmt.where(DBCrossReference.status == status)
        result = await self.db.execute(stmt)
        return [_row_to_cross_reference_dict(r) for r in result.scalars().all()]

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


def _row_to_subreddit_dict(row: DBSubreddit) -> dict:
    return {
        "id": row.id,
        "name": row.name,
        "display_name": row.display_name,
        "description": row.description,
        "purpose": row.purpose or {},
        "output_template": row.output_template or {},
        "participation_model": row.participation_model,
        "tool_configs": row.tool_configs or [],
        "min_agents": row.min_agents,
        "max_agents": row.max_agents,
        "always_include_red_team": row.always_include_red_team,
        "max_cost_per_thread_usd": row.max_cost_per_thread_usd,
        "monthly_budget_usd": row.monthly_budget_usd,
        "engine_overrides": row.engine_overrides,
        "created_by": row.created_by,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }


def _row_to_agent_identity(row: DBAgentIdentity) -> BaseAgentIdentity:
    return BaseAgentIdentity(
        id=UUID(row.id),
        agent_type=row.agent_type,
        display_name=row.display_name,
        expertise_tags=row.expertise_tags or [],
        persona_prompt=row.persona_prompt,
        phase_mandates=row.phase_mandates or {},
        domain_keywords=row.domain_keywords or [],
        knowledge_scope=row.knowledge_scope or [],
        evaluation_criteria=row.evaluation_criteria or {},
        is_red_team=row.is_red_team,
        status=AgentStatus(row.status),
        version=row.version,
        created_at=row.created_at,
    )


def _row_to_membership(row: DBSubredditMembership) -> SubredditMembership:
    return SubredditMembership(
        id=UUID(row.id),
        agent_id=UUID(row.agent_id),
        subreddit_id=UUID(row.subreddit_id),
        role=SubredditRole(row.role),
        role_prompt=row.role_prompt or "",
        tool_access=row.tool_access or [],
        threads_participated=row.threads_participated,
        total_posts=row.total_posts,
        joined_at=row.joined_at,
    )


def _row_to_memory_dict(row: DBSynthesisMemory) -> dict:
    return {
        "id": row.id,
        "thread_id": row.thread_id,
        "subreddit_id": row.subreddit_id,
        "subreddit_name": row.subreddit_name,
        "topic": row.topic,
        "synthesis_content": row.synthesis_content,
        "key_conclusions": row.key_conclusions or [],
        "citations_used": row.citations_used or [],
        "agents_involved": row.agents_involved or [],
        "template_type": row.template_type,
        "confidence_level": row.confidence_level,
        "evidence_quality": row.evidence_quality,
        "confidence_alpha": row.confidence_alpha,
        "confidence_beta": row.confidence_beta,
        "embedding": row.embedding or [],
        "created_at": row.created_at,
    }


def _row_to_cross_reference_dict(row: DBCrossReference) -> dict:
    return {
        "id": row.id,
        "source_memory_id": row.source_memory_id,
        "target_memory_id": row.target_memory_id,
        "source_subreddit_id": row.source_subreddit_id,
        "target_subreddit_id": row.target_subreddit_id,
        "source_subreddit_name": row.source_subreddit_name,
        "target_subreddit_name": row.target_subreddit_name,
        "similarity": row.similarity,
        "shared_entities": row.shared_entities or [],
        "reasoning": row.reasoning,
        "status": row.status,
        "reviewed_by": row.reviewed_by,
        "created_at": row.created_at,
    }
