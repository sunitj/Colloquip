"""Phase 6 repository tests: missions, budgets, approvals, autoresearch runs.

These tests cover the new repository methods added for the Paperclip +
autoresearch integration. Written test-first — they drive the implementation
of SessionRepository.get/update_subreddit_mission, membership budget helpers,
approval queue persistence, and autoresearch run persistence.
"""

from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from colloquip.db.repository import SessionRepository
from colloquip.db.tables import Base
from colloquip.models import (
    ApprovalRequest,
    ApprovalRequestType,
    ApprovalStatus,
    AutoresearchActionType,
    AutoresearchConfig,
    AutoresearchRun,
    AutoresearchStatus,
    AutoresearchStep,
    BaseAgentIdentity,
    MissionObjective,
    SubredditMembership,
    SubredditRole,
)


@pytest.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()


async def _seed_subreddit(repo: SessionRepository, subreddit_id: str = None) -> str:
    sid = subreddit_id or str(uuid4())
    await repo.save_subreddit(
        subreddit_id=sid,
        name=f"oncology-{sid[:8]}",
        display_name="Oncology",
        description="",
    )
    return sid


async def _seed_agent_and_member(
    repo: SessionRepository,
    subreddit_id: str,
    agent_type: str = "adm-et-expert",
) -> tuple[str, str]:
    agent = BaseAgentIdentity(
        agent_type=agent_type,
        display_name="ADMET Expert",
        persona_prompt="",
    )
    await repo.save_agent(agent)
    membership = SubredditMembership(
        agent_id=agent.id,
        subreddit_id=UUID(subreddit_id),
        role=SubredditRole.MEMBER,
    )
    await repo.save_membership(membership)
    return str(agent.id), str(membership.id)


class TestSubredditMissionRepository:
    async def test_missing_mission_returns_empty(self, db_session):
        repo = SessionRepository(db_session)
        sid = await _seed_subreddit(repo)
        await repo.commit()

        mission = await repo.get_subreddit_mission(sid)
        assert mission is not None
        assert mission.subreddit_id == UUID(sid)
        assert mission.mission_md is None
        assert mission.objectives == []
        assert mission.version == 1

    async def test_update_mission_persists_markdown_and_objectives(self, db_session):
        repo = SessionRepository(db_session)
        sid = await _seed_subreddit(repo)
        await repo.commit()

        md = (
            "# Mission\n\n"
            "Understand GLP-1 effects on cognition.\n\n"
            "## Objective: Reduce false claims\n"
            "- metric: citation_verification_rate\n"
            "- target: 0.85\n"
        )
        objectives = [
            MissionObjective(
                id="obj-1",
                title="Reduce false claims",
                metric="citation_verification_rate",
                target=0.85,
            )
        ]
        await repo.update_subreddit_mission(
            subreddit_id=sid,
            mission_md=md,
            objectives=objectives,
            editor="user:123",
        )
        await repo.commit()

        mission = await repo.get_subreddit_mission(sid)
        assert mission.mission_md == md
        assert len(mission.objectives) == 1
        assert mission.objectives[0].metric == "citation_verification_rate"
        assert mission.objectives[0].target == 0.85
        assert mission.version == 2  # bumped on edit

    async def test_get_subreddit_dict_includes_mission_fields(self, db_session):
        """Regression: _row_to_subreddit_dict must surface mission fields.

        Without this, missions persisted to the DB silently disappear
        on reload — the UI shows an empty mission editor even though
        the data is intact in the database.
        """
        repo = SessionRepository(db_session)
        sid = await _seed_subreddit(repo)
        await repo.update_subreddit_mission(
            subreddit_id=sid,
            mission_md="# Mission\n\n## Objective: x\n",
            objectives=[MissionObjective(id="obj-1", title="x")],
        )
        await repo.commit()

        sub = await repo.get_subreddit(sid)
        assert sub is not None
        assert "mission_md" in sub
        assert sub["mission_md"].startswith("# Mission")
        assert "mission_objectives" in sub
        assert len(sub["mission_objectives"]) == 1
        assert sub["mission_version"] == 2

    async def test_update_mission_bumps_version(self, db_session):
        repo = SessionRepository(db_session)
        sid = await _seed_subreddit(repo)
        await repo.commit()

        for i in range(3):
            await repo.update_subreddit_mission(
                subreddit_id=sid,
                mission_md=f"v{i}",
                objectives=[],
                editor="user:x",
            )
        await repo.commit()

        mission = await repo.get_subreddit_mission(sid)
        assert mission.version == 4  # starts at 1, bumped 3 times


class TestAgentBudgetRepository:
    async def test_membership_has_default_none_budgets(self, db_session):
        repo = SessionRepository(db_session)
        sid = await _seed_subreddit(repo)
        await _seed_agent_and_member(repo, sid)
        await repo.commit()

        members = await repo.get_subreddit_members(sid)
        assert len(members) == 1
        m = members[0]
        assert m.max_cost_per_thread_usd is None
        assert m.monthly_budget_usd is None
        assert m.lifetime_cost_usd == 0.0
        assert m.lifetime_input_tokens == 0

    async def test_update_member_budget(self, db_session):
        repo = SessionRepository(db_session)
        sid = await _seed_subreddit(repo)
        agent_id, _ = await _seed_agent_and_member(repo, sid)
        await repo.commit()

        await repo.update_member_budget(
            subreddit_id=sid,
            agent_id=agent_id,
            max_cost_per_thread_usd=1.5,
            monthly_budget_usd=20.0,
        )
        await repo.commit()

        members = await repo.get_subreddit_members(sid)
        m = members[0]
        assert m.max_cost_per_thread_usd == 1.5
        assert m.monthly_budget_usd == 20.0

    async def test_accumulate_member_usage(self, db_session):
        repo = SessionRepository(db_session)
        sid = await _seed_subreddit(repo)
        agent_id, _ = await _seed_agent_and_member(repo, sid)
        await repo.commit()

        await repo.accumulate_member_usage(
            subreddit_id=sid,
            agent_id=agent_id,
            input_tokens=500,
            output_tokens=200,
            cost_usd=0.012,
        )
        await repo.accumulate_member_usage(
            subreddit_id=sid,
            agent_id=agent_id,
            input_tokens=300,
            output_tokens=100,
            cost_usd=0.008,
        )
        await repo.commit()

        members = await repo.get_subreddit_members(sid)
        m = members[0]
        assert m.lifetime_input_tokens == 800
        assert m.lifetime_output_tokens == 300
        assert abs(m.lifetime_cost_usd - 0.020) < 1e-9
        assert abs(m.current_month_cost_usd - 0.020) < 1e-9


class TestApprovalQueueRepository:
    async def test_save_and_list_approval(self, db_session):
        repo = SessionRepository(db_session)
        sid = await _seed_subreddit(repo)
        await repo.commit()

        req = ApprovalRequest(
            subreddit_id=UUID(sid),
            request_type=ApprovalRequestType.BUDGET_OVERRIDE,
            initiator="agent:adm-et-expert",
            payload={"amount": 0.5},
            reason="Needs more tokens to complete analysis",
            estimated_cost_usd=0.5,
        )
        await repo.save_approval_request(req)
        await repo.commit()

        pending = await repo.list_approval_requests(sid, status="pending")
        assert len(pending) == 1
        assert pending[0].id == req.id
        assert pending[0].status == ApprovalStatus.PENDING
        assert pending[0].request_type == ApprovalRequestType.BUDGET_OVERRIDE

    async def test_resolve_approval(self, db_session):
        repo = SessionRepository(db_session)
        sid = await _seed_subreddit(repo)
        await repo.commit()

        req = ApprovalRequest(
            subreddit_id=UUID(sid),
            request_type=ApprovalRequestType.THREAD_SPAWN,
        )
        await repo.save_approval_request(req)
        await repo.commit()

        await repo.resolve_approval_request(
            request_id=req.id,
            status=ApprovalStatus.APPROVED,
            decided_by="user:admin",
        )
        await repo.commit()

        loaded = await repo.get_approval_request(req.id)
        assert loaded is not None
        assert loaded.status == ApprovalStatus.APPROVED
        assert loaded.decided_by == "user:admin"
        assert loaded.decided_at is not None

        pending = await repo.list_approval_requests(sid, status="pending")
        assert len(pending) == 0


class TestAutoresearchRunRepository:
    async def test_save_autoresearch_run(self, db_session):
        repo = SessionRepository(db_session)
        sid = await _seed_subreddit(repo)
        await repo.commit()

        thread_id = uuid4()
        run = AutoresearchRun(
            thread_id=thread_id,
            agent_id="adm-et-expert",
            subreddit_id=UUID(sid),
            config=AutoresearchConfig(max_steps=3, max_tokens=1000),
            scratchpad="# Findings\n\n- Result 1\n",
            steps=[
                AutoresearchStep(
                    step_index=0,
                    action=AutoresearchActionType.SEARCH_PUBMED,
                    rationale="Search for cognition trials",
                    query="GLP-1 cognition",
                    metric_before=0.0,
                    metric_after=0.3,
                    delta=0.3,
                    committed=True,
                    tokens_in=100,
                    tokens_out=50,
                )
            ],
            metric_name="novelty_gain",
            metric_start=0.0,
            metric_end=0.3,
            status=AutoresearchStatus.COMPLETED,
            input_tokens=100,
            output_tokens=50,
            estimated_cost_usd=0.001,
            finished_at=datetime.now(timezone.utc),
        )
        await repo.save_autoresearch_run(run)
        await repo.commit()

        runs = await repo.list_autoresearch_runs(thread_id=thread_id)
        assert len(runs) == 1
        assert runs[0].agent_id == "adm-et-expert"
        assert runs[0].status == AutoresearchStatus.COMPLETED
        assert len(runs[0].steps) == 1
        assert runs[0].steps[0].action == AutoresearchActionType.SEARCH_PUBMED
        assert runs[0].scratchpad.startswith("# Findings")
