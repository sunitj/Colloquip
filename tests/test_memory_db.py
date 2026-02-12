"""Tests for memory DB tables and repository operations."""

from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from colloquip.db.repository import SessionRepository
from colloquip.db.tables import Base
from colloquip.memory.store import SynthesisMemory


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


class TestMemoryRepository:
    @pytest.mark.asyncio
    async def test_save_and_get_memory(self, db_session):
        repo = SessionRepository(db_session)
        mem = SynthesisMemory(
            thread_id=uuid4(),
            subreddit_id=uuid4(),
            subreddit_name="target_validation",
            topic="GLP-1 agonists",
            synthesis_content="Full synthesis text here.",
            key_conclusions=["Conclusion A", "Conclusion B"],
            citations_used=["PUBMED:12345"],
            agents_involved=["biology", "chemistry"],
            template_type="assessment",
            confidence_level="high",
            evidence_quality="moderate",
            embedding=[0.1, 0.2, 0.3],
        )

        await repo.save_memory(mem)
        await repo.commit()

        result = await repo.get_memory(str(mem.id))
        assert result is not None
        assert result["topic"] == "GLP-1 agonists"
        assert result["key_conclusions"] == ["Conclusion A", "Conclusion B"]
        assert result["citations_used"] == ["PUBMED:12345"]
        assert result["embedding"] == [0.1, 0.2, 0.3]

    @pytest.mark.asyncio
    async def test_get_nonexistent_memory(self, db_session):
        repo = SessionRepository(db_session)
        result = await repo.get_memory(str(uuid4()))
        assert result is None

    @pytest.mark.asyncio
    async def test_list_memories(self, db_session):
        repo = SessionRepository(db_session)
        sub_id = uuid4()
        for i in range(3):
            mem = SynthesisMemory(
                thread_id=uuid4(),
                subreddit_id=sub_id,
                subreddit_name="test_sub",
                topic=f"Topic {i}",
                synthesis_content=f"Content {i}",
            )
            await repo.save_memory(mem)
        await repo.commit()

        results = await repo.list_memories(subreddit_id=str(sub_id))
        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_list_memories_all(self, db_session):
        repo = SessionRepository(db_session)
        for i in range(2):
            mem = SynthesisMemory(
                thread_id=uuid4(),
                subreddit_id=uuid4(),
                subreddit_name=f"sub_{i}",
                topic=f"Topic {i}",
                synthesis_content=f"Content {i}",
            )
            await repo.save_memory(mem)
        await repo.commit()

        results = await repo.list_memories()
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_save_and_get_annotation(self, db_session):
        repo = SessionRepository(db_session)
        mem = SynthesisMemory(
            thread_id=uuid4(),
            subreddit_id=uuid4(),
            subreddit_name="test_sub",
            topic="Test topic",
            synthesis_content="Content",
        )
        await repo.save_memory(mem)
        await repo.commit()

        await repo.save_annotation(
            memory_id=str(mem.id),
            annotation_type="correction",
            content="The conclusion about X was later disproven.",
            created_by="researcher@example.com",
        )
        await repo.commit()

        annotations = await repo.get_annotations(str(mem.id))
        assert len(annotations) == 1
        assert annotations[0]["annotation_type"] == "correction"
        assert annotations[0]["content"] == "The conclusion about X was later disproven."
        assert annotations[0]["created_by"] == "researcher@example.com"

    @pytest.mark.asyncio
    async def test_multiple_annotations(self, db_session):
        repo = SessionRepository(db_session)
        mem = SynthesisMemory(
            thread_id=uuid4(),
            subreddit_id=uuid4(),
            subreddit_name="test_sub",
            topic="Test",
            synthesis_content="Content",
        )
        await repo.save_memory(mem)

        await repo.save_annotation(str(mem.id), "confirmed", "Looks correct.")
        await repo.save_annotation(str(mem.id), "context", "Additional context here.")
        await repo.commit()

        annotations = await repo.get_annotations(str(mem.id))
        assert len(annotations) == 2
        types = {a["annotation_type"] for a in annotations}
        assert types == {"confirmed", "context"}

    @pytest.mark.asyncio
    async def test_update_existing_memory(self, db_session):
        repo = SessionRepository(db_session)
        mem = SynthesisMemory(
            thread_id=uuid4(),
            subreddit_id=uuid4(),
            subreddit_name="test_sub",
            topic="Original topic",
            synthesis_content="Original content",
        )
        await repo.save_memory(mem)
        await repo.commit()

        mem.topic = "Updated topic"
        await repo.save_memory(mem)
        await repo.commit()

        result = await repo.get_memory(str(mem.id))
        assert result["topic"] == "Updated topic"
