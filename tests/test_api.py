"""Tests for the Colloquip REST API and WebSocket endpoints."""

import asyncio
import json

import pytest
from httpx import ASGITransport, AsyncClient

from colloquip.api import create_app
from colloquip.api.app import SessionManager


@pytest.fixture
def app():
    """Create a test FastAPI app with a fresh session manager."""
    manager = SessionManager()
    return create_app(session_manager=manager)


@pytest.fixture
async def client(app):
    """Async HTTP client for testing."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


class TestHealth:
    async def test_health_check(self, client):
        resp = await client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}


class TestCreateDeliberation:
    async def test_create_session(self, client):
        resp = await client.post("/api/deliberations", json={
            "hypothesis": "Test hypothesis",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["hypothesis"] == "Test hypothesis"
        assert data["status"] == "pending"
        assert "id" in data

    async def test_create_session_with_options(self, client):
        resp = await client.post("/api/deliberations", json={
            "hypothesis": "Another hypothesis",
            "mode": "mock",
            "seed": 123,
            "max_turns": 10,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["hypothesis"] == "Another hypothesis"

    async def test_create_session_missing_hypothesis(self, client):
        resp = await client.post("/api/deliberations", json={})
        assert resp.status_code == 422

    async def test_create_session_empty_hypothesis(self, client):
        resp = await client.post("/api/deliberations", json={"hypothesis": ""})
        assert resp.status_code == 422

    async def test_create_session_invalid_mode(self, client):
        resp = await client.post("/api/deliberations", json={
            "hypothesis": "Test", "mode": "invalid"
        })
        assert resp.status_code == 422

    async def test_create_session_invalid_max_turns(self, client):
        resp = await client.post("/api/deliberations", json={
            "hypothesis": "Test", "max_turns": 0
        })
        assert resp.status_code == 422


class TestGetSession:
    async def test_get_session(self, client):
        # Create first
        create_resp = await client.post("/api/deliberations", json={
            "hypothesis": "Test hypothesis",
        })
        session_id = create_resp.json()["id"]

        # Retrieve
        resp = await client.get(f"/api/deliberations/{session_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == session_id
        assert data["hypothesis"] == "Test hypothesis"
        assert data["status"] == "pending"
        assert data["phase"] == "explore"
        assert data["post_count"] == 0

    async def test_get_nonexistent_session(self, client):
        from uuid import uuid4
        resp = await client.get(f"/api/deliberations/{uuid4()}")
        assert resp.status_code == 404


class TestGetEnergy:
    async def test_get_energy_empty(self, client):
        create_resp = await client.post("/api/deliberations", json={
            "hypothesis": "Test hypothesis",
        })
        session_id = create_resp.json()["id"]

        resp = await client.get(f"/api/deliberations/{session_id}/energy")
        assert resp.status_code == 200
        data = resp.json()
        assert data["session_id"] == session_id
        assert data["energy_history"] == []


class TestGetPosts:
    async def test_get_posts_empty(self, client):
        create_resp = await client.post("/api/deliberations", json={
            "hypothesis": "Test hypothesis",
        })
        session_id = create_resp.json()["id"]

        resp = await client.get(f"/api/deliberations/{session_id}/posts")
        assert resp.status_code == 200
        assert resp.json()["posts"] == []


class TestSSEStreaming:
    async def test_start_and_stream(self, client):
        """Start a deliberation and verify SSE events are streamed."""
        create_resp = await client.post("/api/deliberations", json={
            "hypothesis": "Test hypothesis",
            "mode": "mock",
            "max_turns": 3,
        })
        session_id = create_resp.json()["id"]

        # Start the deliberation via SSE
        async with client.stream(
            "POST", f"/api/deliberations/{session_id}/start"
        ) as resp:
            assert resp.status_code == 200

            event_types = set()
            count = 0
            async for line in resp.aiter_lines():
                if line.startswith("event:"):
                    event_type = line.split(":", 1)[1].strip()
                    event_types.add(event_type)
                if line.startswith("data:"):
                    count += 1

                # Stop after receiving enough events to validate
                if "done" in event_types or count > 30:
                    break

        # We should see posts, phase changes, and energy updates
        assert "post" in event_types
        assert "energy_update" in event_types

    async def test_start_nonexistent_session(self, client):
        """Starting a non-existent session returns 404."""
        from uuid import uuid4
        resp = await client.post(f"/api/deliberations/{uuid4()}/start")
        assert resp.status_code == 404


class TestIntervention:
    async def test_intervene_nonexistent_session(self, client):
        from uuid import uuid4
        resp = await client.post(
            f"/api/deliberations/{uuid4()}/intervene",
            json={"type": "question", "content": "What about safety?"},
        )
        assert resp.status_code == 404

    async def test_intervene_invalid_type(self, client):
        create_resp = await client.post("/api/deliberations", json={
            "hypothesis": "Test hypothesis",
        })
        session_id = create_resp.json()["id"]
        resp = await client.post(
            f"/api/deliberations/{session_id}/intervene",
            json={"type": "invalid", "content": "Hello"},
        )
        assert resp.status_code == 422

    async def test_intervene_empty_content(self, client):
        create_resp = await client.post("/api/deliberations", json={
            "hypothesis": "Test hypothesis",
        })
        session_id = create_resp.json()["id"]
        resp = await client.post(
            f"/api/deliberations/{session_id}/intervene",
            json={"type": "question", "content": ""},
        )
        assert resp.status_code == 422


class TestGetEvents:
    async def test_get_events_empty(self, client):
        create_resp = await client.post("/api/deliberations", json={
            "hypothesis": "Test hypothesis",
        })
        session_id = create_resp.json()["id"]

        resp = await client.get(f"/api/deliberations/{session_id}/events")
        assert resp.status_code == 200
        assert resp.json()["events"] == []

    async def test_get_events_with_since(self, client):
        create_resp = await client.post("/api/deliberations", json={
            "hypothesis": "Test hypothesis",
        })
        session_id = create_resp.json()["id"]

        resp = await client.get(f"/api/deliberations/{session_id}/events?since=0")
        assert resp.status_code == 200


class TestSessionManager:
    """Unit tests for the SessionManager directly."""

    async def test_create_and_get_session(self):
        manager = SessionManager()
        session = manager.create_session("Test hypothesis")
        assert session.hypothesis == "Test hypothesis"
        assert manager.get_session(session.id) is session

    async def test_subscribe_and_broadcast(self):
        manager = SessionManager()
        session = manager.create_session("Test hypothesis")

        queue = manager.subscribe(session.id)
        await manager._broadcast(session.id, {"type": "test", "data": "hello"})

        event = queue.get_nowait()
        assert event["type"] == "test"
        assert event["data"] == "hello"

    async def test_unsubscribe(self):
        manager = SessionManager()
        session = manager.create_session("Test hypothesis")

        queue = manager.subscribe(session.id)
        manager.unsubscribe(session.id, queue)
        assert queue not in manager.subscribers[session.id]

    async def test_full_deliberation_run(self):
        """Run a full deliberation through the session manager and collect events."""
        manager = SessionManager()
        session = manager.create_session("GLP-1 improves cognition", max_turns=3)

        queue = manager.subscribe(session.id)
        await manager.start_deliberation(session.id)

        events = []
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=10)
                events.append(event)
                if event.get("type") in ("done", "error"):
                    break
            except asyncio.TimeoutError:
                break

        event_types = {e["type"] for e in events}
        assert "post" in event_types
        assert "energy_update" in event_types
        assert "done" in event_types

        # Verify posts were stored
        posts = manager.get_posts(session.id)
        assert len(posts) >= 6  # At least seed posts

        # Verify energy history returns full EnergyUpdate dicts
        energy = manager.get_energy_history(session.id)
        assert len(energy) > 0
        # Each entry should be a dict with turn, energy, and components
        first_entry = energy[0]
        assert isinstance(first_entry, dict)
        assert "energy" in first_entry
        assert "turn" in first_entry
        assert "components" in first_entry

    async def test_session_lock_created(self):
        manager = SessionManager()
        session = manager.create_session("Test hypothesis")
        assert session.id in manager._session_locks

    async def test_start_already_running_returns_error(self):
        """Starting an already-running session raises ValueError."""
        manager = SessionManager()
        session = manager.create_session("Test hypothesis", max_turns=3)
        queue = manager.subscribe(session.id)
        await manager.start_deliberation(session.id)

        with pytest.raises(ValueError, match="already running"):
            await manager.start_deliberation(session.id)

        # Cleanup: wait for deliberation to finish
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=10)
                if event.get("type") in ("done", "error"):
                    break
            except asyncio.TimeoutError:
                break
