"""Tests for API route handlers: export, external, feedback, memory, watcher routes.

Covers happy paths, validation errors, not-found, and service-unavailable for each endpoint.
See tests/TEST_STRATEGY.md for conventions.
"""

from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from colloquip.api import create_app
from colloquip.api.app import SessionManager
from colloquip.memory.store import SynthesisMemory
from colloquip.models import (
    Notification,
    TriageSignal,
)
from colloquip.notifications.store import InMemoryNotificationStore
from colloquip.watchers.interface import WatcherRegistry

# --- Fixtures ---


@pytest.fixture
def manager():
    return SessionManager()


@pytest.fixture
def app(manager):
    return create_app(session_manager=manager)


@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


def _make_memory(subreddit_name="pharma-research", **overrides):
    defaults = dict(
        thread_id=uuid4(),
        subreddit_id=uuid4(),
        subreddit_name=subreddit_name,
        topic="GLP-1 and cognition",
        synthesis_content="GLP-1 may improve cognition.",
        key_conclusions=["GLP-1 is neuroprotective"],
        citations_used=["PUBMED:12345"],
        agents_involved=["biology", "clinical"],
        template_type="research",
        confidence_level="moderate",
        evidence_quality="medium",
    )
    defaults.update(overrides)
    return SynthesisMemory(**defaults)


# =========================================================================
# Export routes
# =========================================================================


class TestExportMarkdown:
    async def test_export_markdown_success(self, manager):
        from unittest.mock import AsyncMock

        from colloquip.models import (
            AgentStance,
            ConsensusMap,
            DeliberationSession,
            Phase,
            Post,
        )

        session = DeliberationSession(hypothesis="Test hypothesis")
        post = Post(
            session_id=session.id,
            agent_id="biology",
            content="GLP-1 is neuroprotective.",
            stance=AgentStance.SUPPORTIVE,
            novelty_score=0.7,
            phase=Phase.EXPLORE,
            key_claims=["GLP-1 is neuroprotective"],
        )
        consensus = ConsensusMap(
            session_id=session.id,
            summary="Multi-agent consensus.",
            agreements=["GLP-1 is neuroprotective"],
            disagreements=["Mechanism unclear"],
        )
        mock_data = {
            "session": session,
            "posts": [post],
            "energy_history": [],
            "consensus": consensus,
        }

        manager.load_session_data = AsyncMock(return_value=mock_data)
        app = create_app(session_manager=manager)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(f"/api/threads/{session.id}/export/markdown")
            assert resp.status_code == 200
            assert "text/markdown" in resp.headers["content-type"]
            assert "attachment" in resp.headers.get("content-disposition", "")
            assert "Test hypothesis" in resp.text
            assert "GLP-1 is neuroprotective" in resp.text

    async def test_export_markdown_not_found(self, client):
        resp = await client.get(f"/api/threads/{uuid4()}/export/markdown")
        assert resp.status_code == 404

    async def test_export_markdown_invalid_uuid(self, client):
        resp = await client.get("/api/threads/not-a-uuid/export/markdown")
        assert resp.status_code == 400


class TestExportJSON:
    async def test_export_json_success(self, manager):
        from unittest.mock import AsyncMock

        from colloquip.models import (
            AgentStance,
            ConsensusMap,
            DeliberationSession,
            EnergyUpdate,
            Phase,
            Post,
        )

        session = DeliberationSession(hypothesis="Test hypothesis")
        post = Post(
            session_id=session.id,
            agent_id="biology",
            content="GLP-1 is neuroprotective.",
            stance=AgentStance.SUPPORTIVE,
            novelty_score=0.7,
            phase=Phase.EXPLORE,
        )
        energy = EnergyUpdate(turn=1, energy=0.8, components={"novelty": 0.9})
        consensus = ConsensusMap(
            session_id=session.id,
            summary="Consensus.",
            agreements=["Point A"],
            disagreements=[],
        )
        mock_data = {
            "session": session,
            "posts": [post],
            "energy_history": [energy],
            "consensus": consensus,
        }

        manager.load_session_data = AsyncMock(return_value=mock_data)
        app = create_app(session_manager=manager)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(f"/api/threads/{session.id}/export/json")
            assert resp.status_code == 200
            data = resp.json()
            assert data["hypothesis"] == "Test hypothesis"
            assert len(data["posts"]) == 1
            assert len(data["energy_history"]) == 1
            assert data["consensus"]["summary"] == "Consensus."
            assert "attachment" in resp.headers.get("content-disposition", "")

    async def test_export_json_not_found(self, client):
        resp = await client.get(f"/api/threads/{uuid4()}/export/json")
        assert resp.status_code == 404

    async def test_export_json_no_consensus(self, manager):
        from unittest.mock import AsyncMock

        from colloquip.models import DeliberationSession

        session = DeliberationSession(hypothesis="Test")
        mock_data = {"session": session, "posts": [], "energy_history": [], "consensus": None}
        manager.load_session_data = AsyncMock(return_value=mock_data)
        app = create_app(session_manager=manager)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(f"/api/threads/{session.id}/export/json")
            assert resp.status_code == 200
            data = resp.json()
            assert "consensus" not in data


# =========================================================================
# External routes
# =========================================================================


class TestExternalSubmit:
    async def test_submit_hypothesis(self, client):
        resp = await client.post(
            "/api/external/submit",
            json={"hypothesis": "GLP-1 improves cognition", "mode": "mock"},
            headers={"X-API-Key": "test-key"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["hypothesis"] == "GLP-1 improves cognition"
        assert data["status"] == "pending"
        assert "thread_id" in data

    async def test_submit_missing_api_key(self, client):
        resp = await client.post(
            "/api/external/submit",
            json={"hypothesis": "GLP-1 improves cognition"},
        )
        assert resp.status_code == 401

    async def test_submit_empty_api_key(self, client):
        resp = await client.post(
            "/api/external/submit",
            json={"hypothesis": "GLP-1 improves cognition"},
            headers={"X-API-Key": ""},
        )
        assert resp.status_code == 401

    async def test_submit_short_hypothesis(self, client):
        resp = await client.post(
            "/api/external/submit",
            json={"hypothesis": "Hi"},
            headers={"X-API-Key": "test-key"},
        )
        assert resp.status_code == 422


class TestExternalResults:
    async def test_get_results(self, client):
        # Create session first
        create_resp = await client.post(
            "/api/external/submit",
            json={"hypothesis": "GLP-1 improves cognition"},
            headers={"X-API-Key": "test-key"},
        )
        thread_id = create_resp.json()["thread_id"]

        resp = await client.get(
            f"/api/external/results/{thread_id}",
            headers={"X-API-Key": "test-key"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["thread_id"] == thread_id
        assert data["status"] == "pending"
        assert data["post_count"] == 0

    async def test_get_results_missing_key(self, client):
        resp = await client.get(f"/api/external/results/{uuid4()}")
        assert resp.status_code == 401

    async def test_get_results_not_found(self, client):
        resp = await client.get(
            f"/api/external/results/{uuid4()}",
            headers={"X-API-Key": "test-key"},
        )
        assert resp.status_code == 404

    async def test_get_results_invalid_uuid(self, client):
        resp = await client.get(
            "/api/external/results/not-a-uuid",
            headers={"X-API-Key": "test-key"},
        )
        assert resp.status_code == 400


# =========================================================================
# Feedback routes
# =========================================================================


@pytest.fixture
async def feedback_client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


class TestReportOutcome:
    async def test_report_outcome_success(self, feedback_client):
        thread_id = str(uuid4())
        resp = await feedback_client.post(
            f"/api/threads/{thread_id}/outcome",
            json={
                "outcome_type": "confirmed",
                "summary": "GLP-1 findings were confirmed in phase 2 trial.",
                "evidence": "Published in Nature Medicine.",
                "agent_assessments": {"biology": "correct", "clinical": "correct"},
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["outcome_type"] == "confirmed"
        assert data["thread_id"] == thread_id

    async def test_report_outcome_invalid_type(self, feedback_client):
        resp = await feedback_client.post(
            f"/api/threads/{uuid4()}/outcome",
            json={
                "outcome_type": "invalid_type",
                "summary": "Some outcome.",
            },
        )
        assert resp.status_code == 422

    async def test_report_outcome_default_tracker(self, client):
        """Outcome tracker is always initialized by create_app."""
        resp = await client.post(
            f"/api/threads/{uuid4()}/outcome",
            json={
                "outcome_type": "confirmed",
                "summary": "Some outcome.",
            },
        )
        assert resp.status_code == 200

    async def test_report_outcome_invalid_uuid(self, feedback_client):
        resp = await feedback_client.post(
            "/api/threads/not-a-uuid/outcome",
            json={
                "outcome_type": "confirmed",
                "summary": "Some outcome.",
            },
        )
        assert resp.status_code == 400


class TestCalibration:
    async def test_agent_calibration_empty(self, feedback_client):
        resp = await feedback_client.get("/api/agents/biology/calibration")
        assert resp.status_code == 200
        data = resp.json()
        assert data["agent_id"] == "biology"
        assert data["total_evaluations"] == 0

    async def test_calibration_overview_empty(self, feedback_client):
        resp = await feedback_client.get("/api/calibration/overview")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_outcomes"] == 0

    async def test_calibration_default_tracker(self, client):
        """Calibration works with default tracker (returns empty data)."""
        resp = await client.get("/api/agents/biology/calibration")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_evaluations"] == 0


# =========================================================================
# Memory routes
# =========================================================================


@pytest.fixture
async def memory_client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


class TestListMemories:
    async def test_list_memories_empty(self, memory_client):
        resp = await memory_client.get("/api/memories")
        assert resp.status_code == 200
        data = resp.json()
        assert data["memories"] == []
        assert data["total"] == 0

    async def test_list_memories_with_data(self, app, memory_client):
        store = app.state.memory_store
        mem = _make_memory()
        await store.save(mem)

        resp = await memory_client.get("/api/memories")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["memories"][0]["topic"] == "GLP-1 and cognition"

    async def test_list_memories_default_store(self, client):
        """Memory store is always initialized by create_app (returns empty list)."""
        resp = await client.get("/api/memories")
        assert resp.status_code == 200
        data = resp.json()
        assert data["memories"] == []


class TestGetMemory:
    async def test_get_memory_success(self, app, memory_client):
        store = app.state.memory_store
        mem = _make_memory()
        await store.save(mem)

        resp = await memory_client.get(f"/api/memories/{mem.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["topic"] == "GLP-1 and cognition"
        assert data["key_conclusions"] == ["GLP-1 is neuroprotective"]

    async def test_get_memory_not_found(self, memory_client):
        resp = await memory_client.get(f"/api/memories/{uuid4()}")
        assert resp.status_code == 404

    async def test_get_memory_invalid_uuid(self, memory_client):
        resp = await memory_client.get("/api/memories/not-a-uuid")
        assert resp.status_code == 400


class TestAnnotateMemory:
    async def test_annotate_success(self, app, memory_client):
        store = app.state.memory_store
        mem = _make_memory()
        await store.save(mem)

        resp = await memory_client.post(
            f"/api/memories/{mem.id}/annotate",
            json={
                "annotation_type": "confirmed",
                "content": "Confirmed by subsequent phase 2 trial.",
                "created_by": "researcher-1",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["annotation_type"] == "confirmed"
        assert data["content"] == "Confirmed by subsequent phase 2 trial."
        assert data["created_by"] == "researcher-1"

    async def test_annotate_memory_not_found(self, memory_client):
        resp = await memory_client.post(
            f"/api/memories/{uuid4()}/annotate",
            json={
                "annotation_type": "confirmed",
                "content": "Confirmed.",
            },
        )
        assert resp.status_code == 404

    async def test_annotate_invalid_type(self, app, memory_client):
        store = app.state.memory_store
        mem = _make_memory()
        await store.save(mem)

        resp = await memory_client.post(
            f"/api/memories/{mem.id}/annotate",
            json={
                "annotation_type": "invalid_type",
                "content": "Something.",
            },
        )
        assert resp.status_code == 422

    async def test_annotate_empty_content(self, app, memory_client):
        store = app.state.memory_store
        mem = _make_memory()
        await store.save(mem)

        resp = await memory_client.post(
            f"/api/memories/{mem.id}/annotate",
            json={
                "annotation_type": "confirmed",
                "content": "",
            },
        )
        assert resp.status_code == 422


class TestSubredditMemories:
    async def test_get_subreddit_memories(self, app, memory_client):
        store = app.state.memory_store
        mem = _make_memory(subreddit_name="pharma-research")
        await store.save(mem)

        resp = await memory_client.get("/api/subreddits/pharma-research/memories")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["memories"][0]["subreddit_name"] == "pharma-research"

    async def test_get_subreddit_memories_no_match(self, app, memory_client):
        store = app.state.memory_store
        mem = _make_memory(subreddit_name="pharma-research")
        await store.save(mem)

        resp = await memory_client.get("/api/subreddits/oncology/memories")
        assert resp.status_code == 200
        assert resp.json()["total"] == 0


# =========================================================================
# Watcher routes
# =========================================================================


@pytest.fixture
def app_with_watchers(manager):
    app = create_app(session_manager=manager)
    app.state.watcher_registry = WatcherRegistry()
    app.state.notification_store = InMemoryNotificationStore()
    return app


@pytest.fixture
async def watcher_client(app_with_watchers):
    transport = ASGITransport(app=app_with_watchers)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


class TestCreateWatcher:
    async def test_create_literature_watcher(self, watcher_client):
        resp = await watcher_client.post(
            "/api/subreddits/pharma-research/watchers",
            json={
                "watcher_type": "literature",
                "name": "GLP-1 literature monitor",
                "query": "GLP-1 receptor agonist cognition",
                "poll_interval_seconds": 3600,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "GLP-1 literature monitor"
        assert data["watcher_type"] == "literature"
        assert data["enabled"] is True

    async def test_create_scheduled_watcher(self, watcher_client):
        resp = await watcher_client.post(
            "/api/subreddits/pharma-research/watchers",
            json={
                "watcher_type": "scheduled",
                "name": "Weekly review",
                "poll_interval_seconds": 86400,
            },
        )
        assert resp.status_code == 200
        assert resp.json()["watcher_type"] == "scheduled"

    async def test_create_webhook_watcher(self, watcher_client):
        resp = await watcher_client.post(
            "/api/subreddits/pharma-research/watchers",
            json={
                "watcher_type": "webhook",
                "name": "CI pipeline hook",
            },
        )
        assert resp.status_code == 200
        assert resp.json()["watcher_type"] == "webhook"

    async def test_create_watcher_no_registry(self, client):
        resp = await client.post(
            "/api/subreddits/pharma-research/watchers",
            json={
                "watcher_type": "literature",
                "name": "Test",
            },
        )
        assert resp.status_code == 503

    async def test_create_watcher_invalid_poll(self, watcher_client):
        resp = await watcher_client.post(
            "/api/subreddits/pharma-research/watchers",
            json={
                "watcher_type": "literature",
                "name": "Test",
                "poll_interval_seconds": 5,  # Below minimum
            },
        )
        assert resp.status_code == 422


class TestListWatchers:
    async def test_list_watchers_empty(self, watcher_client):
        resp = await watcher_client.get("/api/subreddits/pharma-research/watchers")
        assert resp.status_code == 200
        assert resp.json()["total"] == 0

    async def test_list_watchers_filtered(self, watcher_client):
        # Create a watcher first
        await watcher_client.post(
            "/api/subreddits/pharma-research/watchers",
            json={"watcher_type": "webhook", "name": "Test hook"},
        )
        resp = await watcher_client.get("/api/subreddits/pharma-research/watchers")
        assert resp.status_code == 200
        assert resp.json()["total"] == 1


class TestDeleteWatcher:
    async def test_delete_watcher_success(self, watcher_client):
        create_resp = await watcher_client.post(
            "/api/subreddits/pharma-research/watchers",
            json={"watcher_type": "webhook", "name": "To delete"},
        )
        watcher_id = create_resp.json()["id"]

        resp = await watcher_client.delete(f"/api/watchers/{watcher_id}")
        assert resp.status_code == 200
        assert resp.json()["status"] == "deleted"

    async def test_delete_watcher_not_found(self, watcher_client):
        resp = await watcher_client.delete(f"/api/watchers/{uuid4()}")
        assert resp.status_code == 404

    async def test_delete_watcher_invalid_uuid(self, watcher_client):
        resp = await watcher_client.delete("/api/watchers/not-a-uuid")
        assert resp.status_code == 400


class TestNotifications:
    async def test_list_notifications_empty(self, watcher_client):
        resp = await watcher_client.get("/api/notifications")
        assert resp.status_code == 200
        data = resp.json()
        assert data["notifications"] == []
        assert data["total"] == 0

    async def test_list_notifications_with_data(self, app_with_watchers, watcher_client):
        store = app_with_watchers.state.notification_store
        notif = Notification(
            watcher_id=uuid4(),
            event_id=uuid4(),
            subreddit_id=uuid4(),
            title="New GLP-1 paper published",
            summary="A new study on GLP-1 and cognition.",
            signal=TriageSignal.HIGH,
        )
        await store.save(notif)

        resp = await watcher_client.get("/api/notifications")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["notifications"][0]["title"] == "New GLP-1 paper published"

    async def test_list_notifications_invalid_status(self, watcher_client):
        resp = await watcher_client.get("/api/notifications?status=invalid")
        assert resp.status_code == 400

    async def test_act_on_notification(self, app_with_watchers, watcher_client):
        store = app_with_watchers.state.notification_store
        notif = Notification(
            watcher_id=uuid4(),
            event_id=uuid4(),
            subreddit_id=uuid4(),
            title="Test notification",
            summary="Test summary.",
            signal=TriageSignal.MEDIUM,
        )
        await store.save(notif)

        resp = await watcher_client.post(
            f"/api/notifications/{notif.id}/act",
            json={"action": "dismiss"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "acted"
        assert data["action_taken"] == "dismiss"

    async def test_act_notification_not_found(self, watcher_client):
        resp = await watcher_client.post(
            f"/api/notifications/{uuid4()}/act",
            json={"action": "dismiss"},
        )
        assert resp.status_code == 404

    async def test_notifications_no_store(self, client):
        resp = await client.get("/api/notifications")
        assert resp.status_code == 200
        data = resp.json()
        assert data["notifications"] == []
        assert data["total"] == 0


class TestWebhookEndpoint:
    async def test_receive_webhook(self, watcher_client):
        # Create a webhook watcher
        create_resp = await watcher_client.post(
            "/api/subreddits/pharma-research/watchers",
            json={"watcher_type": "webhook", "name": "CI hook"},
        )
        watcher_id = create_resp.json()["id"]

        resp = await watcher_client.post(
            f"/api/webhooks/{watcher_id}",
            json={
                "title": "New build completed",
                "summary": "Build #123 passed.",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "received"
        assert data["watcher_id"] == watcher_id

    async def test_webhook_watcher_not_found(self, watcher_client):
        resp = await watcher_client.post(
            f"/api/webhooks/{uuid4()}",
            json={"title": "Test"},
        )
        assert resp.status_code == 404

    async def test_webhook_wrong_watcher_type(self, watcher_client):
        # Create a literature watcher (not webhook)
        create_resp = await watcher_client.post(
            "/api/subreddits/pharma-research/watchers",
            json={
                "watcher_type": "literature",
                "name": "Lit monitor",
                "query": "GLP-1",
            },
        )
        watcher_id = create_resp.json()["id"]

        resp = await watcher_client.post(
            f"/api/webhooks/{watcher_id}",
            json={"title": "Test"},
        )
        assert resp.status_code == 400
        assert "not a webhook" in resp.json()["detail"].lower()
