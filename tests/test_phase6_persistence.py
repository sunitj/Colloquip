"""Phase 6 persistence integration tests.

Verifies that PlatformManager mutations (mission, budget) and ApprovalQueue
events propagate to the database when ``attach_db`` is configured. These are
the boundary tests that catch the wiring gaps flagged in the PR review:
mutations were silently in-memory only before this fix.
"""

import asyncio

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from colloquip.api.platform_manager import PlatformManager
from colloquip.db.repository import SessionRepository
from colloquip.db.tables import Base
from colloquip.models import (
    ApprovalRequestType,
    ApprovalStatus,
    ParticipationModel,
)


@pytest.fixture
async def db_factory():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    yield factory
    await engine.dispose()


@pytest.fixture
async def pm_with_db(db_factory):
    pm = PlatformManager()
    pm.initialize()
    pm.attach_db(db_factory)
    # Seed an in-memory subreddit + mirror it to DB so mission/budget tests
    # have a row to update.
    result = pm.create_subreddit(
        name="persist_test",
        display_name="Persist Test",
        description="",
        primary_domain="drug_discovery",
        required_expertise=["molecular_biology"],
        participation_model=ParticipationModel.GUIDED,
    )
    sub = result["subreddit"]
    # Persist the subreddit + memberships once so the DB rows exist.
    async with db_factory() as db:
        repo = SessionRepository(db)
        await repo.save_subreddit(
            subreddit_id=sub["id"],
            name=sub["name"],
            display_name=sub["display_name"],
            description=sub["description"],
            purpose=sub["purpose"],
            output_template=sub["output_template"],
            participation_model=sub["participation_model"],
            tool_configs=sub["tool_configs"],
            min_agents=sub.get("min_agents", 3),
            max_agents=sub["max_agents"],
            always_include_red_team=sub["always_include_red_team"],
            max_cost_per_thread_usd=sub["max_cost_per_thread_usd"],
        )
        # Save each member identity + membership row
        members = pm.get_subreddit_members(sub["id"])
        for m in members:
            agent_uuid = m["agent_id"]
            agent = (
                pm.registry.get_agent_by_uuid(agent_uuid)
                if hasattr(pm.registry, "get_agent_by_uuid")
                else None
            )
            if agent is None:
                # Fallback: registry stores by UUID via get_agent
                from uuid import UUID

                agent = pm.registry.get_agent(UUID(agent_uuid))
            if agent is not None:
                await repo.save_agent(agent)
        for m in members:
            from uuid import UUID

            from colloquip.models import SubredditMembership, SubredditRole

            membership = SubredditMembership(
                id=UUID(m["id"]),
                agent_id=UUID(m["agent_id"]),
                subreddit_id=UUID(sub["id"]),
                role=SubredditRole(m.get("role", "member")),
            )
            await repo.save_membership(membership)
        await repo.commit()
    yield pm, sub["id"]


@pytest.mark.asyncio
class TestMissionPersistence:
    async def test_update_mission_writes_to_db(self, pm_with_db, db_factory):
        pm, subreddit_id = pm_with_db

        md = "# Mission\n\n## Objective: Persist me\n- metric: novelty_avg\n- target: 0.4\n"
        pm.update_subreddit_mission(subreddit_id=subreddit_id, mission_md=md)
        # Allow the fire-and-forget persist task to complete
        await asyncio.sleep(0.05)

        # Verify by opening a fresh repo and reading the row
        async with db_factory() as db:
            repo = SessionRepository(db)
            mission = await repo.get_subreddit_mission(subreddit_id)
            assert mission is not None
            assert mission.mission_md is not None
            assert "Persist me" in mission.mission_md
            assert len(mission.objectives) == 1
            assert mission.objectives[0].metric == "novelty_avg"

    async def test_update_member_budget_writes_to_db(self, pm_with_db, db_factory):
        pm, subreddit_id = pm_with_db
        members = pm.get_subreddit_members(subreddit_id)
        agent_id = members[0]["agent_id"]

        pm.set_member_budget(
            subreddit_id=subreddit_id,
            agent_id=agent_id,
            max_cost_per_thread_usd=2.5,
            monthly_budget_usd=50.0,
        )
        await asyncio.sleep(0.05)

        async with db_factory() as db:
            repo = SessionRepository(db)
            db_members = await repo.get_subreddit_members(subreddit_id)
            target = next(m for m in db_members if str(m.agent_id) == agent_id)
            assert target.max_cost_per_thread_usd == 2.5
            assert target.monthly_budget_usd == 50.0


@pytest.mark.asyncio
class TestApprovalPersistence:
    async def test_enqueue_writes_to_db(self, pm_with_db, db_factory):
        pm, subreddit_id = pm_with_db
        from uuid import UUID

        req = pm.approval_queue.enqueue(
            subreddit_id=UUID(subreddit_id),
            request_type=ApprovalRequestType.BUDGET_OVERRIDE,
            initiator="agent:alpha",
            reason="needs more tokens",
            estimated_cost_usd=0.42,
        )
        await asyncio.sleep(0.05)

        async with db_factory() as db:
            repo = SessionRepository(db)
            loaded = await repo.get_approval_request(req.id)
            assert loaded is not None
            assert loaded.status == ApprovalStatus.PENDING
            assert loaded.initiator == "agent:alpha"
            assert loaded.estimated_cost_usd == pytest.approx(0.42)

    async def test_resolve_writes_to_db(self, pm_with_db, db_factory):
        pm, subreddit_id = pm_with_db
        from uuid import UUID

        req = pm.approval_queue.enqueue(
            subreddit_id=UUID(subreddit_id),
            request_type=ApprovalRequestType.TOOL_CALL,
        )
        await asyncio.sleep(0.05)
        pm.approval_queue.resolve(req.id, ApprovalStatus.APPROVED, decided_by="user:admin")
        await asyncio.sleep(0.05)

        async with db_factory() as db:
            repo = SessionRepository(db)
            loaded = await repo.get_approval_request(req.id)
            assert loaded is not None
            assert loaded.status == ApprovalStatus.APPROVED
            assert loaded.decided_by == "user:admin"
