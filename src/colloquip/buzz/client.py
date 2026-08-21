"""WebSocket client for a Buzz relay (NIP-01 wire protocol + NIP-42 auth).

Buzz ships a Rust CLI and no Python SDK, so Colloquip talks the relay protocol
directly. The surface we need is small:

* ``EVENT`` out, ``OK`` back — publish a signed event;
* ``REQ`` out, ``EVENT``/``EOSE`` back — subscribe to a filter;
* ``AUTH`` challenge in, signed ``kind:22242`` back — NIP-42 authentication.

One connection multiplexes everything: a background reader task dispatches
``OK`` frames to per-event futures and ``EVENT`` frames to per-subscription
queues. Publishing auto-reconnects with exponential backoff, and live
subscriptions are re-issued after a reconnect.

Every failure here is non-fatal by design. Mirroring to Buzz must never take a
deliberation down, so the mirror above this layer swallows ``RelayError``.
"""

import asyncio
import json
import logging
import os
import time
from typing import Any, AsyncIterator, Dict, List, Optional

from colloquip.buzz.events import NostrEvent, build_event
from colloquip.buzz.keys import BuzzKeypair
from colloquip.buzz.kinds import KIND_AUTH

logger = logging.getLogger(__name__)

#: Buzz's relay rejects frames above this size (ARCHITECTURE.md).
MAX_FRAME_BYTES = 65_536

#: Buzz caps stored results per filter at 500.
MAX_HISTORICAL_RESULTS = 500

_EOSE = object()


class RelayError(RuntimeError):
    """Raised when the relay rejects an event or the connection fails."""


class _Subscription:
    """One live REQ: a queue of events plus the filters needed to re-issue it."""

    def __init__(self, sub_id: str, filters: List[Dict[str, Any]]):
        self.sub_id = sub_id
        self.filters = filters
        self.queue: asyncio.Queue = asyncio.Queue()
        self.closed = False


class BuzzRelayClient:
    """A single multiplexed connection to a Buzz relay."""

    def __init__(
        self,
        relay_url: str,
        keypair: BuzzKeypair,
        *,
        connect_timeout: float = 10.0,
        publish_timeout: float = 10.0,
        max_reconnect_delay: float = 60.0,
        random_aux: bool = True,
    ):
        self.relay_url = relay_url
        self.keypair = keypair
        self.connect_timeout = connect_timeout
        self.publish_timeout = publish_timeout
        self.max_reconnect_delay = max_reconnect_delay
        self._random_aux = random_aux

        self._ws: Any = None
        self._reader_task: Optional[asyncio.Task] = None
        self._connect_lock = asyncio.Lock()
        self._pending_ok: Dict[str, asyncio.Future] = {}
        self._subscriptions: Dict[str, _Subscription] = {}
        self._sub_counter = 0
        self._authenticated = False
        self._closed = False

    # --- connection lifecycle ---

    @property
    def connected(self) -> bool:
        return self._ws is not None and not self._closed

    async def connect(self) -> None:
        """Open the WebSocket and start the reader loop. Idempotent."""
        async with self._connect_lock:
            if self._ws is not None:
                return
            try:
                import websockets
            except ImportError as exc:  # pragma: no cover - dependency guard
                raise RelayError(
                    "the 'websockets' package is required to talk to a Buzz relay; "
                    "install colloquip[buzz]"
                ) from exc

            logger.info("Connecting to Buzz relay at %s", self.relay_url)
            try:
                self._ws = await asyncio.wait_for(
                    websockets.connect(self.relay_url, max_size=MAX_FRAME_BYTES),
                    timeout=self.connect_timeout,
                )
            except Exception as exc:
                raise RelayError(f"could not connect to {self.relay_url}: {exc}") from exc

            self._closed = False
            self._authenticated = False
            self._reader_task = asyncio.create_task(self._read_loop())

    async def _ensure_connected(self) -> None:
        if self._ws is None:
            await self.connect()
            await self._resubscribe()

    async def close(self) -> None:
        """Close the connection and fail anything still in flight."""
        self._closed = True
        if self._reader_task:
            self._reader_task.cancel()
            try:
                await self._reader_task
            except (asyncio.CancelledError, Exception):  # noqa: BLE001
                pass
            self._reader_task = None
        if self._ws is not None:
            try:
                await self._ws.close()
            except Exception:  # noqa: BLE001 - closing a dead socket is fine
                pass
            self._ws = None
        self._fail_pending(RelayError("relay connection closed"))

    def _fail_pending(self, exc: Exception) -> None:
        for future in self._pending_ok.values():
            if not future.done():
                future.set_exception(exc)
        self._pending_ok.clear()

    # --- reader loop ---

    async def _read_loop(self) -> None:
        ws = self._ws
        try:
            async for raw in ws:
                try:
                    message = json.loads(raw)
                except json.JSONDecodeError:
                    logger.warning("Buzz relay sent malformed JSON: %.120s", raw)
                    continue
                await self._dispatch(message)
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001 - any socket error drops us to reconnect
            logger.warning("Buzz relay connection lost: %s", exc)
        finally:
            if self._ws is ws:
                self._ws = None
                self._authenticated = False
            self._fail_pending(RelayError("relay connection lost"))

    async def _dispatch(self, message: List[Any]) -> None:
        if not isinstance(message, list) or not message:
            return
        verb = message[0]

        if verb == "OK" and len(message) >= 3:
            event_id, accepted = message[1], bool(message[2])
            detail = message[3] if len(message) > 3 else ""
            future = self._pending_ok.pop(event_id, None)
            if future and not future.done():
                future.set_result((accepted, detail))
            elif not accepted:
                logger.warning("Buzz relay rejected event %s: %s", event_id[:8], detail)

        elif verb == "EVENT" and len(message) >= 3:
            sub = self._subscriptions.get(message[1])
            if sub and not sub.closed:
                try:
                    await sub.queue.put(NostrEvent.from_dict(message[2]))
                except (KeyError, TypeError):
                    logger.warning("Buzz relay sent an unparseable event")

        elif verb == "EOSE" and len(message) >= 2:
            sub = self._subscriptions.get(message[1])
            if sub and not sub.closed:
                await sub.queue.put(_EOSE)

        elif verb == "CLOSED" and len(message) >= 2:
            sub = self._subscriptions.get(message[1])
            reason = message[2] if len(message) > 2 else ""
            logger.warning("Buzz relay closed subscription %s: %s", message[1], reason)
            if sub:
                sub.closed = True
                await sub.queue.put(_EOSE)

        elif verb == "AUTH" and len(message) >= 2:
            await self._authenticate(message[1])

        elif verb == "NOTICE" and len(message) >= 2:
            logger.info("Buzz relay notice: %s", message[1])

    # --- NIP-42 ---

    async def _authenticate(self, challenge: str) -> None:
        """Answer the relay's auth challenge with a signed kind:22242 event."""
        event = build_event(
            kind=KIND_AUTH,
            content="",
            keypair=self.keypair,
            tags=[["relay", self.relay_url], ["challenge", challenge]],
            aux_rand=self._aux(),
        )
        await self._send(["AUTH", event.to_dict()])
        self._authenticated = True
        logger.debug("Answered Buzz NIP-42 challenge as %s", self.keypair.public_hex[:8])

    # --- publish ---

    def _aux(self) -> bytes:
        return os.urandom(32) if self._random_aux else b"\x00" * 32

    async def _send(self, message: List[Any]) -> None:
        if self._ws is None:
            raise RelayError("not connected to the relay")
        payload = json.dumps(message, separators=(",", ":"), ensure_ascii=False)
        encoded = payload.encode("utf-8")
        if len(encoded) > MAX_FRAME_BYTES:
            raise RelayError(
                f"frame is {len(encoded)} bytes, over the relay's {MAX_FRAME_BYTES}-byte limit"
            )
        await self._ws.send(payload)

    async def publish(self, event: NostrEvent, *, retries: int = 2) -> bool:
        """Publish a signed event, waiting for the relay's OK.

        Reconnects and retries on transport failure. Returns ``True`` when the
        relay accepted the event; raises ``RelayError`` when it refused it or
        every attempt failed.
        """
        if not event.id or not event.sig:
            raise RelayError("refusing to publish an unsigned event")

        last_error: Optional[Exception] = None
        for attempt in range(retries + 1):
            try:
                await self._ensure_connected()
                future: asyncio.Future = asyncio.get_running_loop().create_future()
                self._pending_ok[event.id] = future
                await self._send(["EVENT", event.to_dict()])
                accepted, detail = await asyncio.wait_for(future, timeout=self.publish_timeout)
                if not accepted:
                    raise RelayError(f"relay rejected kind:{event.kind} event: {detail}")
                return True
            except RelayError:
                self._pending_ok.pop(event.id, None)
                raise
            except (asyncio.TimeoutError, Exception) as exc:  # noqa: BLE001
                self._pending_ok.pop(event.id, None)
                last_error = exc
                if attempt < retries:
                    delay = min(2.0**attempt, self.max_reconnect_delay)
                    logger.warning("Publish to Buzz failed (%s); retrying in %.1fs", exc, delay)
                    await self._drop_connection()
                    await asyncio.sleep(delay)

        raise RelayError(f"could not publish kind:{event.kind} event: {last_error}")

    async def _drop_connection(self) -> None:
        if self._reader_task:
            self._reader_task.cancel()
            self._reader_task = None
        if self._ws is not None:
            try:
                await self._ws.close()
            except Exception:  # noqa: BLE001
                pass
            self._ws = None

    # --- subscribe ---

    def _next_sub_id(self) -> str:
        self._sub_counter += 1
        return f"colloquip-{self._sub_counter}-{int(time.time())}"

    async def _resubscribe(self) -> None:
        """Re-issue live REQs after a reconnect."""
        for sub in list(self._subscriptions.values()):
            if sub.closed:
                continue
            try:
                await self._send(["REQ", sub.sub_id, *sub.filters])
            except Exception as exc:  # noqa: BLE001
                logger.warning("Could not re-issue subscription %s: %s", sub.sub_id, exc)

    async def subscribe(
        self,
        filters: List[Dict[str, Any]],
        *,
        sub_id: Optional[str] = None,
        include_historical: bool = True,
    ) -> AsyncIterator[NostrEvent]:
        """Yield events matching ``filters`` until the iterator is closed.

        With ``include_historical=False``, stored events replayed before EOSE
        are skipped and only newly arriving events are yielded — the right
        choice for reacting to human messages, which must not re-fire on
        reconnect.
        """
        sub_id = sub_id or self._next_sub_id()
        sub = _Subscription(sub_id, filters)

        try:
            # Connect *before* registering: _ensure_connected re-issues every
            # registered subscription, which would duplicate this one's REQ.
            await self._ensure_connected()
            self._subscriptions[sub_id] = sub
            await self._send(["REQ", sub_id, *filters])

            live = include_historical
            while not sub.closed:
                item = await sub.queue.get()
                if item is _EOSE:
                    live = True
                    continue
                if live:
                    yield item
        finally:
            sub.closed = True
            self._subscriptions.pop(sub_id, None)
            if self._ws is not None:
                try:
                    await self._send(["CLOSE", sub_id])
                except Exception:  # noqa: BLE001 - best effort
                    pass


class RecordingRelayClient:
    """An in-memory stand-in for ``BuzzRelayClient``.

    Records everything published and replays injected events to subscribers.
    Used by the test suite, and usable as a dry-run target to inspect exactly
    what Colloquip would send to a relay without operating one.
    """

    def __init__(self, *, accept: bool = True):
        self.published: List[NostrEvent] = []
        self.accept = accept
        self.closed = False
        self._inbound: asyncio.Queue = asyncio.Queue()

    async def connect(self) -> None:
        return None

    async def publish(self, event: NostrEvent, *, retries: int = 2) -> bool:
        if not event.id or not event.sig:
            raise RelayError("refusing to publish an unsigned event")
        if not self.accept:
            raise RelayError("recording client configured to reject")
        self.published.append(event)
        return True

    async def inject(self, event: NostrEvent) -> None:
        """Deliver an event to whatever is currently subscribed."""
        await self._inbound.put(event)

    async def subscribe(
        self,
        filters: List[Dict[str, Any]],
        *,
        sub_id: Optional[str] = None,
        include_historical: bool = True,
    ) -> AsyncIterator[NostrEvent]:
        while not self.closed:
            yield await self._inbound.get()

    async def close(self) -> None:
        self.closed = True

    def published_of_kind(self, kind: int) -> List[NostrEvent]:
        return [e for e in self.published if e.kind == kind]
