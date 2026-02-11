"""Tests for the database persistence layer."""

import pytest
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from colloquip.db.tables import Base
from colloquip.db.repository import SessionRepository
from colloquip.models import (
    AgentStance,
    ConsensusMap,
    DeliberationSession,
    EnergyUpdate,
    Phase,
    Post,
    SessionStatus,
)


@pytest.fixture
async def db_session():
    """Create an in-memory SQLite database for testing."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session

    await engine.dispose()


class TestSessionRepository:
    async def test_save_and_get_session(self, db_session):
        repo = SessionRepository(db_session)
        session = DeliberationSession(hypothesis="GLP-1 improves cognition")

        await repo.save_session(session)
        await repo.commit()

        loaded = await repo.get_session(session.id)
        assert loaded is not None
        assert loaded.hypothesis == "GLP-1 improves cognition"
        assert loaded.status == SessionStatus.PENDING
        assert loaded.phase == Phase.EXPLORE

    async def test_get_nonexistent_session(self, db_session):
        repo = SessionRepository(db_session)
        loaded = await repo.get_session(uuid4())
        assert loaded is None

    async def test_update_session_status(self, db_session):
        repo = SessionRepository(db_session)
        session = DeliberationSession(hypothesis="Test")

        await repo.save_session(session)
        await repo.commit()

        await repo.update_session_status(session.id, SessionStatus.RUNNING, Phase.DEBATE)
        await repo.commit()

        loaded = await repo.get_session(session.id)
        assert loaded.status == SessionStatus.RUNNING
        assert loaded.phase == Phase.DEBATE

    async def test_list_sessions(self, db_session):
        repo = SessionRepository(db_session)

        for i in range(5):
            session = DeliberationSession(hypothesis=f"Hypothesis {i}")
            await repo.save_session(session)
        await repo.commit()

        sessions = await repo.list_sessions(limit=3)
        assert len(sessions) == 3

        all_sessions = await repo.list_sessions()
        assert len(all_sessions) == 5


class TestPostRepository:
    async def test_save_and_get_posts(self, db_session):
        repo = SessionRepository(db_session)

        session = DeliberationSession(hypothesis="Test")
        await repo.save_session(session)

        post = Post(
            session_id=session.id,
            agent_id="biology",
            content="GLP-1 receptor agonists show neuroprotective properties.",
            stance=AgentStance.SUPPORTIVE,
            key_claims=["GLP-1 is neuroprotective"],
            questions_raised=["What is the mechanism?"],
            novelty_score=0.7,
            phase=Phase.EXPLORE,
            triggered_by=["relevance"],
        )
        await repo.save_post(post)
        await repo.commit()

        posts = await repo.get_posts(session.id)
        assert len(posts) == 1
        assert posts[0].agent_id == "biology"
        assert posts[0].content == "GLP-1 receptor agonists show neuroprotective properties."
        assert posts[0].stance == AgentStance.SUPPORTIVE
        assert posts[0].key_claims == ["GLP-1 is neuroprotective"]
        assert posts[0].novelty_score == 0.7
        assert posts[0].phase == Phase.EXPLORE

    async def test_get_posts_ordered(self, db_session):
        repo = SessionRepository(db_session)

        session = DeliberationSession(hypothesis="Test")
        await repo.save_session(session)

        for i in range(3):
            post = Post(
                session_id=session.id,
                agent_id=f"agent_{i}",
                content=f"Post {i}",
                stance=AgentStance.NEUTRAL,
                novelty_score=0.5,
                phase=Phase.EXPLORE,
            )
            await repo.save_post(post)
        await repo.commit()

        posts = await repo.get_posts(session.id)
        assert len(posts) == 3
        assert posts[0].agent_id == "agent_0"
        assert posts[2].agent_id == "agent_2"


class TestEnergyRepository:
    async def test_save_and_get_energy(self, db_session):
        repo = SessionRepository(db_session)

        session = DeliberationSession(hypothesis="Test")
        await repo.save_session(session)

        update = EnergyUpdate(
            turn=1,
            energy=0.85,
            components={"novelty": 0.9, "disagreement": 0.3, "questions": 0.5, "staleness": 0.1},
        )
        await repo.save_energy_update(session.id, update)
        await repo.commit()

        history = await repo.get_energy_history(session.id)
        assert len(history) == 1
        assert history[0].turn == 1
        assert history[0].energy == 0.85
        assert history[0].components["novelty"] == 0.9


class TestConsensusRepository:
    async def test_save_and_get_consensus(self, db_session):
        repo = SessionRepository(db_session)

        session = DeliberationSession(hypothesis="Test")
        await repo.save_session(session)

        consensus = ConsensusMap(
            session_id=session.id,
            summary="Multi-agent analysis concluded...",
            agreements=["GLP-1 is neuroprotective"],
            disagreements=["Mechanism unclear"],
            minority_positions=["May cause side effects"],
            final_stances={"biology": AgentStance.SUPPORTIVE, "red_team": AgentStance.CRITICAL},
        )
        await repo.save_consensus(consensus)
        await repo.commit()

        loaded = await repo.get_consensus(session.id)
        assert loaded is not None
        assert loaded.summary == "Multi-agent analysis concluded..."
        assert loaded.agreements == ["GLP-1 is neuroprotective"]
        assert loaded.final_stances["biology"] == AgentStance.SUPPORTIVE
        assert loaded.final_stances["red_team"] == AgentStance.CRITICAL

    async def test_get_nonexistent_consensus(self, db_session):
        repo = SessionRepository(db_session)
        loaded = await repo.get_consensus(uuid4())
        assert loaded is None


class TestListSessions:
    async def test_list_sessions_endpoint(self):
        """Test the list sessions API endpoint."""
        from httpx import ASGITransport, AsyncClient
        from colloquip.api import create_app
        from colloquip.api.app import SessionManager

        manager = SessionManager()
        app = create_app(session_manager=manager)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Create two sessions
            await client.post("/api/deliberations", json={"hypothesis": "Test 1"})
            await client.post("/api/deliberations", json={"hypothesis": "Test 2"})

            # List sessions
            resp = await client.get("/api/deliberations")
            assert resp.status_code == 200
            data = resp.json()
            assert len(data["sessions"]) == 2

            # Verify fields
            s = data["sessions"][0]
            assert "id" in s
            assert "hypothesis" in s
            assert "status" in s
            assert "phase" in s
            assert "created_at" in s
