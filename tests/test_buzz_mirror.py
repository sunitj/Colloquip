"""BuzzMirror mapping tests.

Every test runs against ``RecordingRelayClient``, so the suite exercises the
real signing and mapping code with no relay and no network.
"""

import asyncio
import json

import pytest

from colloquip.buzz.client import RecordingRelayClient, RelayError
from colloquip.buzz.events import build_event, channel_tag, root_tag
from colloquip.buzz.keys import derive_agent_keypair
from colloquip.buzz.kinds import (
    KIND_ADD_USER,
    KIND_CHAT,
    KIND_COLLOQUIP_BUDGET_SKIP,
    KIND_COLLOQUIP_CONSENSUS,
    KIND_COLLOQUIP_ENERGY,
    KIND_COLLOQUIP_PHASE,
    KIND_COLLOQUIP_POST,
    KIND_COLLOQUIP_THREAD,
    KIND_CREATE_GROUP,
    KIND_PROFILE,
    KIND_REACTION,
)
from colloquip.buzz.mirror import BuzzMirror, json_content, parse_intervention_type

SERVICE = derive_agent_keypair("service-seed", "colloquip-service")
AGENT_SEED = "agent-seed"
CHANNEL = "11111111-1111-1111-1111-111111111111"
SESSION = "22222222-2222-2222-2222-222222222222"


@pytest.fixture
def client():
    return RecordingRelayClient()


@pytest.fixture
def mirror(client):
    return BuzzMirror(client, SERVICE, AGENT_SEED)


@pytest.fixture
async def threaded(mirror, client):
    """A mirror with an open thread, and the recording cleared."""
    await mirror.open_thread(SESSION, CHANNEL, "Title", "The hypothesis")
    client.published.clear()
    return mirror


def post_event(**overrides):
    data = {
        "id": "aaaa",
        "session_id": SESSION,
        "agent_id": "biology",
        "content": "Mitochondrial density is the confound here.",
        "stance": "support",
        "phase": "debate",
        "novelty_score": 0.8,
        "key_claims": ["density matters"],
        "questions_raised": ["what about controls?"],
        "citations": [],
    }
    data.update(overrides)
    return {"type": "post", "data": data}


class TestChannelsAndAgents:
    async def test_ensure_channel_publishes_a_create_group_event(self, mirror, client):
        await mirror.ensure_channel(CHANNEL, "oncology", "Tumor biology deliberations")
        (event,) = client.published_of_kind(KIND_CREATE_GROUP)
        assert event.channel == CHANNEL
        assert event.tag_value("name") == "oncology"
        assert event.pubkey == SERVICE.public_hex
        assert event.verify()

    async def test_ensure_channel_is_idempotent(self, mirror, client):
        await mirror.ensure_channel(CHANNEL, "oncology")
        await mirror.ensure_channel(CHANNEL, "oncology")
        assert len(client.published_of_kind(KIND_CREATE_GROUP)) == 1

    async def test_agents_are_announced_with_their_own_key(self, mirror, client):
        await mirror.announce_agent("biology", "Dr. Bio", "A cell biologist.")
        (event,) = client.published_of_kind(KIND_PROFILE)
        assert event.pubkey == mirror.agent_pubkey("biology")
        assert event.pubkey != SERVICE.public_hex
        assert json.loads(event.content)["display_name"] == "Dr. Bio"

    async def test_agents_are_announced_only_once(self, mirror, client):
        await mirror.announce_agent("biology", "Dr. Bio")
        await mirror.announce_agent("biology", "Dr. Bio")
        assert len(client.published_of_kind(KIND_PROFILE)) == 1

    async def test_register_community_creates_channel_profiles_and_memberships(
        self, mirror, client
    ):
        await mirror.register_community(
            CHANNEL,
            "oncology",
            "Tumor biology",
            [
                {"agent_id": "biology", "display_name": "Dr. Bio"},
                {"agent_id": "red_team", "display_name": "The Skeptic"},
            ],
        )
        assert len(client.published_of_kind(KIND_CREATE_GROUP)) == 1
        assert len(client.published_of_kind(KIND_PROFILE)) == 2
        adds = client.published_of_kind(KIND_ADD_USER)
        assert len(adds) == 2
        assert {e.tag_value("p") for e in adds} == {
            mirror.agent_pubkey("biology"),
            mirror.agent_pubkey("red_team"),
        }

    def test_agent_keys_are_stable_and_distinct(self, mirror):
        assert mirror.agent_pubkey("biology") == mirror.agent_pubkey("biology")
        assert mirror.agent_pubkey("biology") != mirror.agent_pubkey("chemistry")

    def test_own_pubkeys_are_recognised(self, mirror):
        assert mirror.is_own_pubkey(SERVICE.public_hex)
        assert mirror.is_own_pubkey(mirror.agent_pubkey("biology"))
        assert not mirror.is_own_pubkey("ff" * 32)


class TestThreads:
    async def test_open_thread_announces_and_records_the_root(self, mirror, client):
        root_id = await mirror.open_thread(SESSION, CHANNEL, "Title", "The hypothesis")

        chat = client.published_of_kind(KIND_CHAT)[0]
        assert chat.id == root_id
        assert "Title" in chat.content and "The hypothesis" in chat.content
        assert chat.channel == CHANNEL

        (meta,) = client.published_of_kind(KIND_COLLOQUIP_THREAD)
        assert json.loads(meta.content)["hypothesis"] == "The hypothesis"
        assert root_id in meta.tag_values("e")

    async def test_open_thread_creates_the_channel_when_missing(self, mirror, client):
        await mirror.open_thread(SESSION, CHANNEL, "Title", "Hypothesis")
        assert len(client.published_of_kind(KIND_CREATE_GROUP)) == 1

    async def test_events_for_an_unknown_session_are_skipped(self, mirror, client):
        await mirror.mirror_event("no-such-session", post_event())
        assert client.published == []


class TestPostMirroring:
    async def test_a_post_yields_prose_and_a_structured_payload(self, threaded, client):
        await threaded.mirror_event(SESSION, post_event())

        chat = client.published_of_kind(KIND_CHAT)[0]
        payload = client.published_of_kind(KIND_COLLOQUIP_POST)[0]

        assert chat.content == "Mitochondrial density is the confound here."
        assert json.loads(payload.content)["novelty_score"] == 0.8
        assert chat.verify() and payload.verify()

    async def test_posts_are_signed_by_the_agent_not_the_service(self, threaded, client):
        await threaded.mirror_event(SESSION, post_event())
        for event in client.published:
            assert event.pubkey == threaded.agent_pubkey("biology")
            assert event.pubkey != SERVICE.public_hex

    async def test_different_agents_sign_with_different_keys(self, threaded, client):
        await threaded.mirror_event(SESSION, post_event(agent_id="biology"))
        await threaded.mirror_event(SESSION, post_event(agent_id="red_team"))
        pubkeys = {e.pubkey for e in client.published_of_kind(KIND_COLLOQUIP_POST)}
        assert len(pubkeys) == 2

    async def test_posts_carry_thread_channel_and_stance_tags(self, threaded, client):
        await threaded.mirror_event(SESSION, post_event())
        payload = client.published_of_kind(KIND_COLLOQUIP_POST)[0]
        assert payload.channel == CHANNEL
        assert payload.tag_value("colloquip_session") == SESSION
        assert payload.tag_value("colloquip_stance") == "support"
        assert payload.tag_value("colloquip_phase") == "debate"

    async def test_the_payload_links_back_to_its_prose_event(self, threaded, client):
        await threaded.mirror_event(SESSION, post_event())
        chat = client.published_of_kind(KIND_CHAT)[0]
        payload = client.published_of_kind(KIND_COLLOQUIP_POST)[0]
        assert chat.id in payload.tag_values("e")

    async def test_posts_are_threaded_under_the_session_root(self, mirror, client):
        root_id = await mirror.open_thread(SESSION, CHANNEL, "Title", "Hypothesis")
        client.published.clear()
        await mirror.mirror_event(SESSION, post_event())
        assert root_tag(root_id) in client.published_of_kind(KIND_COLLOQUIP_POST)[0].tags

    async def test_overlong_content_is_truncated_to_fit_a_frame(self, threaded, client):
        await threaded.mirror_event(SESSION, post_event(content="x" * 100_000))
        chat = client.published_of_kind(KIND_CHAT)[0]
        assert len(chat.content) < 40_000 and chat.content.endswith("...")


class TestTelemetryMirroring:
    async def test_phase_changes_publish_a_note_and_a_payload(self, threaded, client):
        await threaded.mirror_event(
            SESSION,
            {
                "type": "phase_change",
                "data": {"current_phase": "converge", "confidence": 0.82, "metrics": {}},
            },
        )
        assert "converge" in client.published_of_kind(KIND_CHAT)[0].content
        payload = client.published_of_kind(KIND_COLLOQUIP_PHASE)[0]
        assert json.loads(payload.content)["current_phase"] == "converge"

    async def test_energy_updates_use_an_ephemeral_kind_and_no_prose(self, threaded, client):
        await threaded.mirror_event(
            SESSION, {"type": "energy_update", "data": {"turn": 3, "energy": 0.55}}
        )
        assert client.published_of_kind(KIND_CHAT) == []
        payload = client.published_of_kind(KIND_COLLOQUIP_ENERGY)[0]
        assert json.loads(payload.content)["energy"] == 0.55

    async def test_energy_can_be_switched_off(self, client):
        mirror = BuzzMirror(client, SERVICE, AGENT_SEED, publish_energy=False)
        await mirror.open_thread(SESSION, CHANNEL, "T", "H")
        client.published.clear()
        await mirror.mirror_event(SESSION, {"type": "energy_update", "data": {"energy": 0.1}})
        assert client.published == []

    async def test_budget_skips_are_surfaced_to_humans(self, threaded, client):
        await threaded.mirror_event(
            SESSION,
            {
                "type": "budget_skip",
                "data": {"agent_id": "chemistry", "reason": "monthly budget exhausted"},
            },
        )
        assert "monthly budget exhausted" in client.published_of_kind(KIND_CHAT)[0].content
        assert len(client.published_of_kind(KIND_COLLOQUIP_BUDGET_SKIP)) == 1

    async def test_the_consensus_map_is_rendered_as_a_readable_synthesis(self, threaded, client):
        await threaded.mirror_event(
            SESSION,
            {
                "type": "session_complete",
                "data": {
                    "summary": "Plausible but unproven.",
                    "agreements": ["mechanism is coherent"],
                    "disagreements": ["dosing is unresolved"],
                    "minority_positions": [],
                },
            },
        )
        prose = client.published_of_kind(KIND_CHAT)[0].content
        assert "Plausible but unproven." in prose
        assert "mechanism is coherent" in prose
        assert "dosing is unresolved" in prose
        assert "Minority positions" not in prose  # empty sections are omitted
        assert len(client.published_of_kind(KIND_COLLOQUIP_CONSENSUS)) == 1

    async def test_lifecycle_events_are_not_mirrored(self, threaded, client):
        await threaded.mirror_event(SESSION, {"type": "done", "data": None})
        await threaded.mirror_event(SESSION, {"type": "error", "data": {"message": "boom"}})
        assert client.published == []

    async def test_unknown_event_types_are_ignored(self, threaded, client):
        await threaded.mirror_event(SESSION, {"type": "something_new", "data": {}})
        assert client.published == []

    async def test_prose_can_be_switched_off(self, client):
        mirror = BuzzMirror(client, SERVICE, AGENT_SEED, publish_prose=False)
        await mirror.open_thread(SESSION, CHANNEL, "T", "H")
        client.published.clear()
        await mirror.mirror_event(SESSION, post_event())
        assert client.published_of_kind(KIND_CHAT) == []
        assert len(client.published_of_kind(KIND_COLLOQUIP_POST)) == 1


class TestFailureIsolation:
    async def test_relay_failures_never_propagate(self):
        client = RecordingRelayClient(accept=False)
        mirror = BuzzMirror(client, SERVICE, AGENT_SEED)
        await mirror.open_thread(SESSION, CHANNEL, "T", "H")
        await mirror.mirror_event(SESSION, post_event())  # must not raise
        assert mirror.stats["failed"] > 0
        assert mirror.stats["published"] == 0

    async def test_a_thread_still_opens_when_the_announcement_fails(self):
        client = RecordingRelayClient(accept=False)
        mirror = BuzzMirror(client, SERVICE, AGENT_SEED)
        assert await mirror.open_thread(SESSION, CHANNEL, "T", "H") is None

    def test_fire_and_forget_helpers_do_not_raise_without_a_loop(self, mirror):
        mirror.mirror_event_nowait(SESSION, post_event())  # no running loop

    async def test_fire_and_forget_helpers_publish_on_the_loop(self, mirror, client):
        mirror.open_thread_nowait(SESSION, CHANNEL, "T", "H")
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        assert client.published_of_kind(KIND_COLLOQUIP_THREAD)


class TestInboundEvents:
    async def _watch(self, mirror, received, kind="on_message"):
        async def handler(session_id, content, event):
            received.append((session_id, content))

        task = asyncio.create_task(mirror.watch_channel(CHANNEL, **{kind: handler}))
        await asyncio.sleep(0)
        return task

    async def test_a_human_message_tagged_with_the_session_is_routed(self, threaded, client):
        received = []
        task = await self._watch(threaded, received)

        human = derive_agent_keypair("human-seed", "alice")
        await client.inject(
            build_event(
                KIND_CHAT,
                "What about renal clearance?",
                human,
                tags=[channel_tag(CHANNEL), ["colloquip_session", SESSION]],
            )
        )
        await asyncio.sleep(0.05)
        task.cancel()

        assert received == [(SESSION, "What about renal clearance?")]

    async def test_a_reply_in_the_thread_resolves_to_its_session(self, mirror, client):
        root_id = await mirror.open_thread(SESSION, CHANNEL, "T", "H")
        received = []
        task = await self._watch(mirror, received)

        human = derive_agent_keypair("human-seed", "alice")
        await client.inject(
            build_event(
                KIND_CHAT, "Follow-up", human, tags=[channel_tag(CHANNEL), root_tag(root_id)]
            )
        )
        await asyncio.sleep(0.05)
        task.cancel()

        assert received == [(SESSION, "Follow-up")]

    async def test_colloquips_own_events_are_never_fed_back_in(self, threaded, client):
        received = []
        task = await self._watch(threaded, received)

        threaded.agent_keypair("biology")  # ensure the key is known
        for keypair in (SERVICE, derive_agent_keypair(AGENT_SEED, "biology")):
            await client.inject(
                build_event(
                    KIND_CHAT,
                    "agent output",
                    keypair,
                    tags=[channel_tag(CHANNEL), ["colloquip_session", SESSION]],
                )
            )
        await asyncio.sleep(0.05)
        task.cancel()

        assert received == []

    async def test_messages_with_no_session_context_are_ignored(self, threaded, client):
        received = []
        task = await self._watch(threaded, received)

        human = derive_agent_keypair("human-seed", "alice")
        await client.inject(
            build_event(KIND_CHAT, "just chatting", human, tags=[channel_tag(CHANNEL)])
        )
        await asyncio.sleep(0.05)
        task.cancel()

        assert received == []

    async def test_reactions_are_routed_to_their_own_handler(self, threaded, client):
        received = []
        task = await self._watch(threaded, received, kind="on_reaction")

        human = derive_agent_keypair("human-seed", "alice")
        await client.inject(
            build_event(
                KIND_REACTION,
                "+",
                human,
                tags=[channel_tag(CHANNEL), ["colloquip_session", SESSION]],
            )
        )
        await asyncio.sleep(0.05)
        task.cancel()

        assert received == [(SESSION, "+")]

    async def test_a_failing_handler_does_not_kill_the_watcher(self, threaded, client):
        seen = []

        async def handler(session_id, content, event):
            seen.append(content)
            if content == "boom":
                raise RuntimeError("handler exploded")

        task = asyncio.create_task(threaded.watch_channel(CHANNEL, on_message=handler))
        await asyncio.sleep(0)

        human = derive_agent_keypair("human-seed", "alice")
        for content in ("boom", "still here"):
            await client.inject(
                build_event(
                    KIND_CHAT,
                    content,
                    human,
                    tags=[channel_tag(CHANNEL), ["colloquip_session", SESSION]],
                )
            )
        await asyncio.sleep(0.05)
        task.cancel()

        assert seen == ["boom", "still here"]

    async def test_watching_with_no_handlers_is_a_no_op(self, threaded):
        await threaded.watch_channel(CHANNEL)  # returns immediately


class TestHelpers:
    @pytest.mark.parametrize(
        "content,expected",
        [
            ("What about X?", "question"),
            ("!question is this dosing right?", "question"),
            ("!data here is the trial readout", "data"),
            ("!redirect focus on safety", "redirect"),
            ("!terminate", "terminate"),
            ("!stop", "terminate"),
            ("!TERMINATE", "terminate"),
        ],
    )
    def test_intervention_types_are_parsed_from_commands(self, content, expected):
        assert parse_intervention_type(content)[0] == expected

    def test_the_command_prefix_is_stripped_from_the_content(self):
        assert parse_intervention_type("!data trial readout attached")[1] == (
            "trial readout attached"
        )

    def test_a_bare_command_keeps_its_text_so_content_is_never_empty(self):
        assert parse_intervention_type("!terminate")[1] == "!terminate"

    def test_plain_messages_default_to_questions(self):
        assert parse_intervention_type("  hello  ") == ("question", "hello")

    def test_json_content_parses_payloads(self):
        event = build_event(KIND_COLLOQUIP_POST, '{"a": 1}', SERVICE)
        assert json_content(event) == {"a": 1}

    def test_json_content_returns_none_for_prose(self):
        assert json_content(build_event(KIND_CHAT, "not json", SERVICE)) is None

    def test_json_content_returns_none_for_non_objects(self):
        assert json_content(build_event(KIND_CHAT, "[1,2,3]", SERVICE)) is None


class TestLifecycle:
    async def test_describe_reports_operational_state(self, threaded):
        await threaded.mirror_event(SESSION, post_event())
        described = threaded.describe()
        assert described["service_pubkey"] == SERVICE.public_hex
        assert described["service_npub"].startswith("npub1")
        assert described["channels"] == [CHANNEL]
        assert described["threads"] == 1
        assert "biology" in described["agents"]
        assert described["stats"]["published"] > 0

    async def test_close_cancels_watchers_and_closes_the_client(self, threaded, client):
        async def handler(session_id, content, event):
            pass

        threaded.start_watching(CHANNEL, on_message=handler)
        await asyncio.sleep(0)
        await threaded.close()
        assert client.closed

    def test_start_watching_without_a_loop_is_a_no_op(self, mirror):
        mirror.start_watching(CHANNEL, on_message=None)


def test_unsigned_events_are_never_published():
    from colloquip.buzz.events import NostrEvent

    client = RecordingRelayClient()
    unsigned = NostrEvent(kind=KIND_CHAT, content="x", pubkey=SERVICE.public_hex)
    with pytest.raises(RelayError):
        asyncio.run(client.publish(unsigned))
