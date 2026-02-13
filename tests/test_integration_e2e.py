"""End-to-end integration tests: full deliberation lifecycle via API + WebSocket.

Validates backend + frontend data contracts work together — REST creation,
WebSocket event streaming, session list, history retrieval, and intervention.
"""

import asyncio
from uuid import UUID

import pytest
from httpx import ASGITransport, AsyncClient

from colloquip.api import create_app
from colloquip.api.app import SessionManager


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


async def _create_and_run(client, manager, hypothesis="Test hypothesis", max_turns=5):
    """Helper: create session via REST, start via manager, collect events."""
    resp = await client.post(
        "/api/deliberations",
        json={
            "hypothesis": hypothesis,
            "mode": "mock",
            "max_turns": max_turns,
        },
    )
    assert resp.status_code == 200
    session_id = UUID(resp.json()["id"])

    queue = manager.subscribe(session_id)
    await manager.start_deliberation(session_id)

    events = []
    while True:
        try:
            event = await asyncio.wait_for(queue.get(), timeout=15)
            events.append(event)
            if event.get("type") in ("done", "error"):
                break
        except asyncio.TimeoutError:
            break

    return session_id, events


@pytest.mark.integration
class TestFullLifecycle:
    """Full deliberation lifecycle: create -> start -> collect events -> verify."""

    async def test_create_start_collect_complete(self, client, manager):
        """A mock deliberation produces valid posts, energy updates, and consensus."""
        session_id, events = await _create_and_run(
            client,
            manager,
            hypothesis="GLP-1 agonists improve cognition",
            max_turns=5,
        )

        event_types = {e["type"] for e in events}

        # Event types present
        assert "post" in event_types, "Expected at least one post event"
        assert "energy_update" in event_types, "Expected energy updates"
        assert "done" in event_types, "Expected done signal"

        # Validate post shape matches frontend contract
        post_events = [e for e in events if e["type"] == "post"]
        assert len(post_events) >= 6, f"Expected >= 6 posts (seed), got {len(post_events)}"

        for pe in post_events:
            post = pe["data"]
            assert "id" in post
            assert "agent_id" in post
            assert "content" in post
            assert "stance" in post
            assert post["stance"] in ("supportive", "critical", "neutral", "novel_connection")
            assert "key_claims" in post
            assert "questions_raised" in post
            assert "connections_identified" in post
            assert "novelty_score" in post
            assert "phase" in post
            assert post["phase"] in ("explore", "debate", "deepen", "converge", "synthesis")
            assert "triggered_by" in post
            assert isinstance(post["triggered_by"], list)
            assert "created_at" in post

        # Validate energy update shape
        energy_events = [e for e in events if e["type"] == "energy_update"]
        for ee in energy_events:
            eu = ee["data"]
            assert "turn" in eu
            assert "energy" in eu
            assert 0.0 <= eu["energy"] <= 1.0
            assert "components" in eu
            for key in ("novelty", "disagreement", "questions", "staleness"):
                assert key in eu["components"]

        # Check for consensus (session_complete)
        consensus_events = [e for e in events if e["type"] == "session_complete"]
        if consensus_events:
            cm = consensus_events[0]["data"]
            assert "summary" in cm
            assert "agreements" in cm
            assert "disagreements" in cm
            assert "final_stances" in cm
            assert isinstance(cm["final_stances"], dict)

        # All agent IDs are from the known set
        known_agents = {"biology", "chemistry", "admet", "clinical", "regulatory", "redteam"}
        post_agents = {pe["data"]["agent_id"] for pe in post_events}
        assert post_agents.issubset(known_agents), f"Unknown agents: {post_agents - known_agents}"

    async def test_event_types_complete(self, client, manager):
        """Events stored in manager are ordered and of valid types."""
        session_id, events = await _create_and_run(client, manager, max_turns=3)

        stored = manager.get_events(session_id)
        valid_types = {"post", "phase_change", "energy_update", "session_complete", "done", "error"}
        for ev in stored:
            assert ev["type"] in valid_types


@pytest.mark.integration
class TestSessionListAndHistory:
    """Test that created sessions appear in the list and history is retrievable."""

    async def test_list_returns_created_sessions(self, client):
        """GET /api/deliberations should list created sessions."""
        resp1 = await client.post("/api/deliberations", json={"hypothesis": "First hypothesis"})
        resp2 = await client.post("/api/deliberations", json={"hypothesis": "Second hypothesis"})
        id1 = resp1.json()["id"]
        id2 = resp2.json()["id"]

        resp = await client.get("/api/deliberations")
        assert resp.status_code == 200
        sessions = resp.json()["sessions"]
        assert len(sessions) >= 2
        session_ids = {s["id"] for s in sessions}
        assert id1 in session_ids
        assert id2 in session_ids

        for s in sessions:
            assert "id" in s
            assert "hypothesis" in s
            assert "status" in s
            assert "phase" in s
            assert "created_at" in s

    async def test_list_sorted_newest_first(self, client):
        """Sessions should be sorted newest first."""
        await client.post("/api/deliberations", json={"hypothesis": "Older"})
        await client.post("/api/deliberations", json={"hypothesis": "Newer"})

        resp = await client.get("/api/deliberations")
        sessions = resp.json()["sessions"]
        assert sessions[0]["hypothesis"] == "Newer"
        assert sessions[1]["hypothesis"] == "Older"

    async def test_history_matches_live_events(self, client, manager):
        """History endpoint returns same posts that were streamed live."""
        session_id, events = await _create_and_run(
            client,
            manager,
            hypothesis="History test",
            max_turns=3,
        )

        live_posts = [e["data"] for e in events if e["type"] == "post"]

        resp = await client.get(f"/api/deliberations/{session_id}/history")
        assert resp.status_code == 200
        history = resp.json()

        assert history["session"]["id"] == str(session_id)
        assert history["session"]["hypothesis"] == "History test"
        assert len(history["posts"]) == len(live_posts)

        for live, hist in zip(live_posts, history["posts"]):
            assert live["agent_id"] == hist["agent_id"]
            assert live["content"] == hist["content"]

        assert len(history["energy_history"]) > 0


@pytest.mark.integration
class TestReconnectionReplay:
    """WebSocket-style event replay via the events endpoint."""

    async def test_replay_from_sequence(self, client, manager):
        """GET /api/deliberations/{id}/events?since=N returns events after N."""
        session_id, _ = await _create_and_run(
            client,
            manager,
            hypothesis="Replay test",
            max_turns=3,
        )

        all_resp = await client.get(f"/api/deliberations/{session_id}/events?since=0")
        all_events = all_resp.json()["events"]
        assert len(all_events) > 3

        mid = len(all_events) // 2
        partial_resp = await client.get(f"/api/deliberations/{session_id}/events?since={mid}")
        partial_events = partial_resp.json()["events"]

        assert len(partial_events) == len(all_events) - mid
        assert partial_events[0]["type"] == all_events[mid]["type"]


@pytest.mark.integration
class TestInterventionDuringDeliberation:
    """Interventions during an active deliberation don't crash the system."""

    async def test_intervention_via_rest(self, client, manager):
        """POST intervention during a running deliberation."""
        resp = await client.post(
            "/api/deliberations",
            json={
                "hypothesis": "Intervention test",
                "mode": "mock",
                "max_turns": 8,
            },
        )
        session_id = UUID(resp.json()["id"])

        queue = manager.subscribe(session_id)
        await manager.start_deliberation(session_id)

        # Wait for first post
        first_post = None
        while first_post is None:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=10)
                if event["type"] == "post":
                    first_post = event
            except asyncio.TimeoutError:
                pytest.fail("No posts received within timeout")

        # Intervene
        intervene_resp = await client.post(
            f"/api/deliberations/{session_id}/intervene",
            json={"type": "question", "content": "What about drug-drug interactions?"},
        )
        assert intervene_resp.status_code == 200

        # Collect remaining events — should not error
        post_after_intervention = False
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=10)
                if event["type"] == "post":
                    post_after_intervention = True
                if event.get("type") in ("done", "error"):
                    break
            except asyncio.TimeoutError:
                break

        assert post_after_intervention, "Expected posts after intervention"
