"""Wire-protocol tests for BuzzRelayClient against an in-process relay stub.

The stub speaks the subset of NIP-01/NIP-42 that Buzz's relay speaks, so these
exercise the real WebSocket client: the auth handshake, OK correlation,
subscription fan-out, EOSE handling, and reconnection.
"""

import asyncio
import json

import pytest

websockets = pytest.importorskip("websockets")

from colloquip.buzz.client import MAX_FRAME_BYTES, BuzzRelayClient, RelayError  # noqa: E402
from colloquip.buzz.events import build_event  # noqa: E402
from colloquip.buzz.keys import derive_agent_keypair  # noqa: E402
from colloquip.buzz.kinds import KIND_AUTH, KIND_CHAT  # noqa: E402
from colloquip.buzz.schnorr import schnorr_verify  # noqa: E402

KEYPAIR = derive_agent_keypair("client-test", "service")


class StubRelay:
    """A minimal Nostr relay for testing the client end of the protocol."""

    def __init__(self, *, require_auth=False, reject_events=False, challenge="chal-123"):
        self.require_auth = require_auth
        self.reject_events = reject_events
        self.challenge = challenge
        self.received: list = []
        self.auth_events: list = []
        self.subscriptions: dict = {}
        self.connections = 0
        self._server = None
        self.url = ""

    async def __aenter__(self):
        self._server = await websockets.serve(self._handle, "127.0.0.1", 0)
        port = self._server.sockets[0].getsockname()[1]
        self.url = f"ws://127.0.0.1:{port}"
        return self

    async def __aexit__(self, *exc):
        self._server.close()
        await self._server.wait_closed()

    async def _handle(self, ws):
        self.connections += 1
        if self.require_auth:
            await ws.send(json.dumps(["AUTH", self.challenge]))
        try:
            async for raw in ws:
                message = json.loads(raw)
                self.received.append(message)
                await self._on_message(ws, message)
        except websockets.exceptions.ConnectionClosed:
            pass

    async def _on_message(self, ws, message):
        verb = message[0]
        if verb == "AUTH":
            self.auth_events.append(message[1])
            await ws.send(json.dumps(["OK", message[1]["id"], True, ""]))
        elif verb == "EVENT":
            event = message[1]
            if self.reject_events:
                await ws.send(json.dumps(["OK", event["id"], False, "blocked: test rejection"]))
            else:
                await ws.send(json.dumps(["OK", event["id"], True, ""]))
        elif verb == "REQ":
            sub_id = message[1]
            self.subscriptions[sub_id] = ws
            await ws.send(json.dumps(["EOSE", sub_id]))
        elif verb == "CLOSE":
            self.subscriptions.pop(message[1], None)

    async def push(self, sub_id, event):
        await self.subscriptions[sub_id].send(json.dumps(["EVENT", sub_id, event.to_dict()]))

    async def push_raw(self, sub_id, frame):
        await self.subscriptions[sub_id].send(frame)

    async def drop_connections(self):
        for ws in list(self.subscriptions.values()):
            await ws.close()
        self.subscriptions.clear()


def chat(content="hello", keypair=KEYPAIR):
    return build_event(KIND_CHAT, content, keypair)


@pytest.mark.integration
class TestPublishing:
    async def test_a_published_event_is_accepted(self):
        async with StubRelay() as relay:
            client = BuzzRelayClient(relay.url, KEYPAIR)
            try:
                assert await client.publish(chat()) is True
                assert relay.received[0][0] == "EVENT"
            finally:
                await client.close()

    async def test_the_event_arrives_intact_and_verifiable(self):
        async with StubRelay() as relay:
            client = BuzzRelayClient(relay.url, KEYPAIR)
            try:
                event = chat("mitochondrió — π")
                await client.publish(event)
            finally:
                await client.close()
            delivered = relay.received[0][1]
            assert delivered["content"] == "mitochondrió — π"
            assert schnorr_verify(
                bytes.fromhex(delivered["id"]),
                bytes.fromhex(delivered["pubkey"]),
                bytes.fromhex(delivered["sig"]),
            )

    async def test_a_rejection_raises(self):
        async with StubRelay(reject_events=True) as relay:
            client = BuzzRelayClient(relay.url, KEYPAIR)
            try:
                with pytest.raises(RelayError, match="test rejection"):
                    await client.publish(chat())
            finally:
                await client.close()

    async def test_unsigned_events_are_refused_before_the_wire(self):
        from colloquip.buzz.events import NostrEvent

        client = BuzzRelayClient("ws://unused", KEYPAIR)
        unsigned = NostrEvent(kind=KIND_CHAT, content="x", pubkey=KEYPAIR.public_hex)
        with pytest.raises(RelayError, match="unsigned"):
            await client.publish(unsigned)

    async def test_oversized_frames_are_refused(self):
        async with StubRelay() as relay:
            client = BuzzRelayClient(relay.url, KEYPAIR)
            try:
                with pytest.raises(RelayError, match="byte limit"):
                    await client.publish(chat("x" * MAX_FRAME_BYTES), retries=0)
            finally:
                await client.close()

    async def test_concurrent_publishes_correlate_their_own_oks(self):
        async with StubRelay() as relay:
            client = BuzzRelayClient(relay.url, KEYPAIR)
            try:
                events = [chat(f"message {i}") for i in range(10)]
                assert all(await asyncio.gather(*(client.publish(e) for e in events)))
                sent = {m[1]["id"] for m in relay.received if m[0] == "EVENT"}
                assert sent == {e.id for e in events}
            finally:
                await client.close()

    async def test_an_unreachable_relay_raises_rather_than_hanging(self):
        client = BuzzRelayClient("ws://127.0.0.1:1", KEYPAIR, connect_timeout=1.0)
        with pytest.raises(RelayError):
            await client.publish(chat(), retries=0)


@pytest.mark.integration
class TestAuthentication:
    async def test_the_client_answers_a_nip42_challenge(self):
        async with StubRelay(require_auth=True) as relay:
            client = BuzzRelayClient(relay.url, KEYPAIR)
            try:
                await client.publish(chat())
            finally:
                await client.close()

            assert relay.auth_events, "client never answered the AUTH challenge"
            auth = relay.auth_events[0]
            assert auth["kind"] == KIND_AUTH
            assert auth["pubkey"] == KEYPAIR.public_hex
            tags = {t[0]: t[1] for t in auth["tags"]}
            assert tags["challenge"] == "chal-123"
            assert tags["relay"] == relay.url
            assert schnorr_verify(
                bytes.fromhex(auth["id"]), bytes.fromhex(auth["pubkey"]), bytes.fromhex(auth["sig"])
            )


@pytest.mark.integration
class TestSubscriptions:
    async def test_events_pushed_by_the_relay_are_yielded(self):
        async with StubRelay() as relay:
            client = BuzzRelayClient(relay.url, KEYPAIR)
            received = []

            async def consume():
                async for event in client.subscribe([{"kinds": [KIND_CHAT]}]):
                    received.append(event)

            task = asyncio.create_task(consume())
            try:
                await asyncio.sleep(0.2)
                sub_id = next(iter(relay.subscriptions))
                await relay.push(sub_id, chat("from the relay"))
                await asyncio.sleep(0.2)
            finally:
                task.cancel()
                await asyncio.gather(task, return_exceptions=True)
                await client.close()

            assert [e.content for e in received] == ["from the relay"]

    async def test_the_req_carries_the_filters_verbatim(self):
        async with StubRelay() as relay:
            client = BuzzRelayClient(relay.url, KEYPAIR)
            filters = [{"kinds": [9, 7], "#h": ["chan-1"]}]

            async def consume():
                async for _ in client.subscribe(filters):
                    pass

            task = asyncio.create_task(consume())
            try:
                await asyncio.sleep(0.2)
                req = next(m for m in relay.received if m[0] == "REQ")
                assert req[2:] == filters
            finally:
                task.cancel()
                await asyncio.gather(task, return_exceptions=True)
                await client.close()

    async def test_historical_events_are_skipped_when_asked(self):
        """Events before EOSE are replay; only live ones may become interventions."""
        async with StubRelay() as relay:
            client = BuzzRelayClient(relay.url, KEYPAIR)
            received = []

            # Send a "stored" event before EOSE, then a live one after.
            original = relay._on_message

            async def with_history(ws, message):
                if message[0] == "REQ":
                    sub_id = message[1]
                    relay.subscriptions[sub_id] = ws
                    await ws.send(json.dumps(["EVENT", sub_id, chat("historical").to_dict()]))
                    await ws.send(json.dumps(["EOSE", sub_id]))
                else:
                    await original(ws, message)

            relay._on_message = with_history

            async def consume():
                async for event in client.subscribe(
                    [{"kinds": [KIND_CHAT]}], include_historical=False
                ):
                    received.append(event)

            task = asyncio.create_task(consume())
            try:
                await asyncio.sleep(0.2)
                sub_id = next(iter(relay.subscriptions))
                await relay.push(sub_id, chat("live"))
                await asyncio.sleep(0.2)
            finally:
                task.cancel()
                await asyncio.gather(task, return_exceptions=True)
                await client.close()

            assert [e.content for e in received] == ["live"]

    async def test_closing_the_iterator_closes_the_subscription(self):
        async with StubRelay() as relay:
            client = BuzzRelayClient(relay.url, KEYPAIR)

            async def consume():
                async for _ in client.subscribe([{"kinds": [KIND_CHAT]}]):
                    pass

            task = asyncio.create_task(consume())
            await asyncio.sleep(0.2)
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
            await asyncio.sleep(0.1)
            await client.close()

            assert any(m[0] == "CLOSE" for m in relay.received)

    async def test_malformed_frames_do_not_kill_the_connection(self):
        async with StubRelay() as relay:
            client = BuzzRelayClient(relay.url, KEYPAIR)
            received = []

            async def consume():
                async for event in client.subscribe([{"kinds": [KIND_CHAT]}]):
                    received.append(event)

            task = asyncio.create_task(consume())
            try:
                await asyncio.sleep(0.2)
                sub_id = next(iter(relay.subscriptions))
                await relay.push_raw(sub_id, "not json at all")
                await relay.push_raw(sub_id, json.dumps(["EVENT", sub_id, {"bogus": True}]))
                await relay.push_raw(sub_id, json.dumps(["NOTICE", "just so you know"]))
                await relay.push(sub_id, chat("still working"))
                await asyncio.sleep(0.2)
            finally:
                task.cancel()
                await asyncio.gather(task, return_exceptions=True)
                await client.close()

            assert [e.content for e in received] == ["still working"]


@pytest.mark.integration
class TestReconnection:
    async def test_publishing_reconnects_after_the_connection_drops(self):
        async with StubRelay() as relay:
            client = BuzzRelayClient(relay.url, KEYPAIR, publish_timeout=2.0)
            try:
                await client.publish(chat("first"))
                assert relay.connections == 1

                await client._drop_connection()
                await asyncio.sleep(0.1)

                await client.publish(chat("second"))
                assert relay.connections == 2
            finally:
                await client.close()

    async def test_close_is_idempotent(self):
        async with StubRelay() as relay:
            client = BuzzRelayClient(relay.url, KEYPAIR)
            await client.publish(chat())
            await client.close()
            await client.close()
            assert not client.connected


@pytest.mark.integration
async def test_subscribe_issues_exactly_one_req():
    """Regression: registering before connecting made _resubscribe duplicate it."""
    async with StubRelay() as relay:
        client = BuzzRelayClient(relay.url, KEYPAIR)

        async def consume():
            async for _ in client.subscribe([{"kinds": [KIND_CHAT]}]):
                pass

        task = asyncio.create_task(consume())
        try:
            await asyncio.sleep(0.2)
            assert len([m for m in relay.received if m[0] == "REQ"]) == 1
        finally:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
            await client.close()
