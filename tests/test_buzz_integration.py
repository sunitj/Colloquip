"""End-to-end tests: a real deliberation mirrored onto a (recording) relay.

These run the actual engine in mock mode through ``SessionManager``, with the
Buzz mirror attached exactly as ``create_app`` attaches it in production. They
prove the adapter is a projection: with it attached the deliberation produces
the same events it always did, plus a signed mirror.
"""

import asyncio
import json
from uuid import UUID

import pytest
from httpx import ASGITransport, AsyncClient

from colloquip.api import create_app
from colloquip.api.app import SessionManager
from colloquip.api.platform_manager import PlatformManager
from colloquip.buzz.client import RecordingRelayClient
from colloquip.buzz.events import build_event, channel_tag
from colloquip.buzz.keys import derive_agent_keypair
from colloquip.buzz.kinds import (
    KIND_ADD_USER,
    KIND_CHAT,
    KIND_COLLOQUIP_CONSENSUS,
    KIND_COLLOQUIP_ENERGY,
    KIND_COLLOQUIP_POST,
    KIND_COLLOQUIP_THREAD,
    KIND_CREATE_GROUP,
    KIND_PROFILE,
)
from colloquip.buzz.mirror import BuzzMirror

SERVICE = derive_agent_keypair("integration-service", "colloquip")


@pytest.fixture
def relay():
    return RecordingRelayClient()


@pytest.fixture
def mirror(relay):
    return BuzzMirror(relay, SERVICE, "integration-agent-seed")


@pytest.fixture
def manager(mirror):
    manager = SessionManager()
    manager.attach_buzz(mirror)
    return manager


@pytest.fixture
async def client(manager):
    transport = ASGITransport(app=create_app(session_manager=manager))
    async with AsyncClient(transport=transport, base_url="http://test") as http:
        yield http


async def run_deliberation(client, manager, max_turns=3):
    """Create and run a short mock deliberation, returning its events."""
    resp = await client.post(
        "/api/deliberations",
        json={"hypothesis": "Compound X inhibits kinase Y", "mode": "mock", "max_turns": max_turns},
    )
    assert resp.status_code == 200
    session_id = UUID(resp.json()["id"])

    queue = manager.subscribe(session_id)
    await manager.start_deliberation(session_id)

    events = []
    while True:
        try:
            event = await asyncio.wait_for(queue.get(), timeout=15)
        except asyncio.TimeoutError:
            break
        events.append(event)
        if event.get("type") in ("done", "error"):
            break

    # Mirroring is fire-and-forget; let the scheduled publishes drain.
    for _ in range(50):
        await asyncio.sleep(0)
    return session_id, events


@pytest.mark.integration
class TestMirroredDeliberation:
    async def test_a_deliberation_is_mirrored_to_the_relay(self, client, manager, relay):
        session_id, events = await run_deliberation(client, manager)

        assert any(e["type"] == "post" for e in events)
        assert relay.published, "nothing reached the relay"

        broadcast_posts = [e for e in events if e["type"] == "post"]
        mirrored_posts = relay.published_of_kind(KIND_COLLOQUIP_POST)
        assert len(mirrored_posts) == len(broadcast_posts)

    async def test_every_mirrored_event_is_a_valid_signed_event(self, client, manager, relay):
        await run_deliberation(client, manager)
        assert relay.published
        for event in relay.published:
            assert event.verify(), f"kind:{event.kind} failed signature verification"

    async def test_the_thread_is_announced_before_any_post(self, client, manager, relay):
        await run_deliberation(client, manager)
        kinds = [e.kind for e in relay.published]
        assert kinds.index(KIND_COLLOQUIP_THREAD) < kinds.index(KIND_COLLOQUIP_POST)

    async def test_posts_are_attributed_to_their_agent_not_the_service(
        self, client, manager, relay, mirror
    ):
        await run_deliberation(client, manager)
        for event in relay.published_of_kind(KIND_COLLOQUIP_POST):
            agent_id = json.loads(event.content)["agent_id"]
            assert event.pubkey == mirror.agent_pubkey(agent_id)
            assert event.pubkey != SERVICE.public_hex

    async def test_multiple_agents_appear_as_distinct_identities(self, client, manager, relay):
        await run_deliberation(client, manager)
        pubkeys = {e.pubkey for e in relay.published_of_kind(KIND_COLLOQUIP_POST)}
        assert len(pubkeys) > 1

    async def test_energy_and_synthesis_reach_the_relay(self, client, manager, relay):
        await run_deliberation(client, manager)
        assert relay.published_of_kind(KIND_COLLOQUIP_ENERGY)
        assert relay.published_of_kind(KIND_COLLOQUIP_CONSENSUS)

    async def test_every_event_carries_the_session_tag(self, client, manager, relay):
        session_id, _ = await run_deliberation(client, manager)
        tagged = [e for e in relay.published if e.tag_value("colloquip_session")]
        assert tagged
        assert {e.tag_value("colloquip_session") for e in tagged} == {str(session_id)}

    async def test_no_event_exceeds_the_relay_frame_limit(self, client, manager, relay):
        from colloquip.buzz.client import MAX_FRAME_BYTES

        await run_deliberation(client, manager)
        for event in relay.published:
            encoded = json.dumps(["EVENT", event.to_dict()], separators=(",", ":"))
            assert len(encoded.encode("utf-8")) <= MAX_FRAME_BYTES


@pytest.mark.integration
class TestMirrorIsNonIntrusive:
    async def test_a_dead_relay_does_not_break_a_deliberation(self, mirror):
        """The whole point of option B: Buzz being down costs nothing."""
        manager = SessionManager()
        dead = RecordingRelayClient(accept=False)
        manager.attach_buzz(BuzzMirror(dead, SERVICE, "seed"))

        transport = ASGITransport(app=create_app(session_manager=manager))
        async with AsyncClient(transport=transport, base_url="http://test") as http:
            _, events = await run_deliberation(http, manager)

        assert any(e["type"] == "post" for e in events)
        assert events[-1]["type"] == "done"

    async def test_events_match_a_run_with_no_mirror_attached(self):
        """Attaching the mirror must not change what subscribers see."""

        async def event_types(attach: bool):
            manager = SessionManager()
            if attach:
                manager.attach_buzz(BuzzMirror(RecordingRelayClient(), SERVICE, "seed"))
            transport = ASGITransport(app=create_app(session_manager=manager))
            async with AsyncClient(transport=transport, base_url="http://test") as http:
                _, events = await run_deliberation(http, manager)
            return [e["type"] for e in events]

        assert await event_types(attach=True) == await event_types(attach=False)


@pytest.mark.integration
class TestInboundInterventions:
    async def test_a_human_message_in_buzz_becomes_an_intervention(self, manager, relay, mirror):
        """A human typing in the Buzz channel injects energy into the session."""
        session = manager.create_session(hypothesis="Compound X works", mode="mock")
        for _ in range(20):
            await asyncio.sleep(0)

        await manager.start_deliberation(session.id)
        await asyncio.sleep(0.1)

        channel = "colloquip-default"
        human = derive_agent_keypair("human", "reviewer")
        await relay.inject(
            build_event(
                KIND_CHAT,
                "!data the phase II readout was negative",
                human,
                tags=[channel_tag(channel), ["colloquip_session", str(session.id)]],
            )
        )
        await asyncio.sleep(0.2)

        task = manager._running_tasks.get(session.id)
        if task and not task.done():
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)

        # The intervention is recorded as a post authored by the human channel.
        contents = [p.content for p in manager.posts[session.id]]
        assert any("phase II readout was negative" in c for c in contents)

    async def test_interventions_can_be_refused(self, mirror):
        manager = SessionManager()
        manager.attach_buzz(mirror, accept_interventions=False)
        session = manager.create_session(hypothesis="H", mode="mock")

        await manager._handle_buzz_message(str(session.id), "a question", None)
        assert manager.posts[session.id] == []

    async def test_messages_for_unknown_sessions_are_ignored(self, manager):
        await manager._handle_buzz_message("not-a-uuid", "hello", None)
        await manager._handle_buzz_message(str(UUID(int=9)), "hello", None)

    async def test_empty_messages_are_ignored(self, manager):
        session = manager.create_session(hypothesis="H", mode="mock")
        await manager._handle_buzz_message(str(session.id), "   ", None)
        assert manager.posts[session.id] == []


@pytest.mark.integration
class TestCommunityMirroring:
    async def test_creating_a_subreddit_mirrors_the_community(self, mirror, relay):
        platform = PlatformManager()
        platform.initialize()
        platform.attach_buzz(mirror)

        result = platform.create_subreddit(
            name="oncology", display_name="Oncology", description="Tumor biology"
        )
        for _ in range(50):
            await asyncio.sleep(0)

        (channel,) = relay.published_of_kind(KIND_CREATE_GROUP)
        assert channel.channel == result["subreddit"]["id"]
        assert channel.tag_value("name") == "Oncology"

        profiles = relay.published_of_kind(KIND_PROFILE)
        assert profiles, "no agent profiles were published"
        assert len(relay.published_of_kind(KIND_ADD_USER)) == len(profiles)

    async def test_mirrored_agent_ids_match_the_ids_posts_use(self, mirror, relay):
        """Profiles must key on agent_type, or posts show up as strangers."""
        platform = PlatformManager()
        platform.initialize()
        platform.attach_buzz(mirror)
        platform.create_subreddit(name="onc", display_name="Onc", description="")
        for _ in range(50):
            await asyncio.sleep(0)

        profile_pubkeys = {e.pubkey for e in relay.published_of_kind(KIND_PROFILE)}
        agent_types = {
            json.loads(e.content)["colloquip_agent_id"]
            for e in relay.published_of_kind(KIND_PROFILE)
        }
        assert profile_pubkeys == {mirror.agent_pubkey(a) for a in agent_types}

    async def test_a_failing_mirror_does_not_break_subreddit_creation(self):
        platform = PlatformManager()
        platform.initialize()
        platform.attach_buzz(BuzzMirror(RecordingRelayClient(accept=False), SERVICE, "seed"))

        result = platform.create_subreddit(name="onc", display_name="Onc", description="")
        for _ in range(50):
            await asyncio.sleep(0)
        assert result["subreddit"]["name"] == "onc"


@pytest.mark.integration
class TestStatusEndpoint:
    async def test_status_reports_disabled_when_no_mirror_is_attached(self):
        transport = ASGITransport(app=create_app(session_manager=SessionManager()))
        async with AsyncClient(transport=transport, base_url="http://test") as http:
            body = (await http.get("/api/buzz/status")).json()
        assert body["enabled"] is False
        assert "BUZZ_ENABLED" in body["reason"]

    async def test_status_reports_the_mirror_when_attached(self, client, manager, mirror):
        # create_app leaves app.state.buzz_mirror unset outside the lifespan,
        # so attach it the way the lifespan hook does.
        client._transport.app.state.buzz_mirror = mirror
        body = (await client.get("/api/buzz/status")).json()
        assert body["enabled"] is True
        assert body["service_pubkey"] == SERVICE.public_hex
