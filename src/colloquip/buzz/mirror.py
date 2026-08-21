"""BuzzMirror — projects Colloquip deliberations onto a Buzz relay.

Colloquip keeps its own Postgres, its own repository layer, and its own SPA.
The mirror is a *projection* on top of that: every event the ``SessionManager``
broadcasts is also published to a Buzz relay as a signed Nostr event, and
messages humans type in the Buzz channel come back as interventions.

The mapping:

===========================  ==================================================
Colloquip                    Buzz
===========================  ==================================================
``Subreddit``                channel (``kind:9007``), channel id = subreddit id
``Thread`` / session         NIP-10 thread rooted at a ``kind:9`` announcement
``Post``                     ``kind:9`` prose + ``kind:41000`` structured payload
``AgentIdentity``            a derived keypair with a ``kind:0`` profile
``PhaseSignal``              ``kind:41001``
``EnergyUpdate``             ``kind:20100`` (ephemeral — Redis fan-out only)
``AgentBudgetSkipped``       ``kind:41003`` + a human-readable note
``ConsensusMap``             ``kind:41002`` + a human-readable summary
human message in channel     ``HumanIntervention``
===========================  ==================================================

Two rules hold throughout:

1. **Never break a deliberation.** Every relay failure is caught, counted, and
   logged. A relay outage degrades Colloquip to exactly its current behaviour.
2. **Buzz is a mirror, not the system of record.** Nothing reads back from the
   relay to reconstruct state; Postgres remains authoritative.
"""

import asyncio
import json
import logging
from typing import Any, Awaitable, Callable, Dict, List, Optional, Protocol

from colloquip.buzz.client import RelayError
from colloquip.buzz.events import NostrEvent, build_event, build_json_event, channel_tag, root_tag
from colloquip.buzz.keys import BuzzKeypair, derive_agent_keypair
from colloquip.buzz.kinds import (
    EVENT_TYPE_TO_KIND,
    KIND_ADD_USER,
    KIND_CHAT,
    KIND_COLLOQUIP_ENERGY,
    KIND_COLLOQUIP_THREAD,
    KIND_CREATE_GROUP,
    KIND_PROFILE,
    KIND_REACTION,
    is_ephemeral,
)

logger = logging.getLogger(__name__)

#: Prose bodies are trimmed well below the relay's 64 KB frame limit so the
#: JSON envelope and tags always fit alongside them.
MAX_CONTENT_CHARS = 32_000


class RelayClientProtocol(Protocol):
    """The slice of ``BuzzRelayClient`` the mirror depends on."""

    async def publish(self, event: NostrEvent, *, retries: int = 2) -> bool: ...

    def subscribe(self, filters: List[Dict[str, Any]], **kwargs: Any) -> Any: ...

    async def close(self) -> None: ...


def _truncate(text: str, limit: int = MAX_CONTENT_CHARS) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


class BuzzMirror:
    """Publishes Colloquip activity to a Buzz relay and listens for humans."""

    def __init__(
        self,
        client: RelayClientProtocol,
        service_keypair: BuzzKeypair,
        agent_key_seed: str,
        *,
        publish_energy: bool = True,
        publish_prose: bool = True,
    ):
        self._client = client
        self._service = service_keypair
        self._agent_seed = agent_key_seed
        self._publish_energy = publish_energy
        self._publish_prose = publish_prose

        self._agent_keys: Dict[str, BuzzKeypair] = {}
        self._announced_agents: set[str] = set()
        self._channels: set[str] = set()
        # session id -> (channel id, root event id) for NIP-10 threading
        self._threads: Dict[str, tuple[str, Optional[str]]] = {}
        self._watchers: List[asyncio.Task] = []
        self._background: set[asyncio.Task] = set()

        self.stats: Dict[str, int] = {"published": 0, "failed": 0, "received": 0}

    # --- identities ---

    @property
    def service_pubkey(self) -> str:
        return self._service.public_hex

    def agent_keypair(self, agent_id: str) -> BuzzKeypair:
        """The stable keypair for an agent, derived on first use."""
        if agent_id not in self._agent_keys:
            self._agent_keys[agent_id] = derive_agent_keypair(self._agent_seed, agent_id)
        return self._agent_keys[agent_id]

    def agent_pubkey(self, agent_id: str) -> str:
        return self.agent_keypair(agent_id).public_hex

    def is_own_pubkey(self, pubkey: str) -> bool:
        """True when the pubkey belongs to Colloquip itself, not a human."""
        if pubkey == self._service.public_hex:
            return True
        return any(kp.public_hex == pubkey for kp in self._agent_keys.values())

    # --- publishing primitives ---

    async def _publish(self, event: NostrEvent, description: str) -> bool:
        """Publish, swallowing relay failures so callers can't be broken by them."""
        try:
            await self._client.publish(event)
            self.stats["published"] += 1
            return True
        except RelayError as exc:
            self.stats["failed"] += 1
            # An unrecognised ephemeral kind is a relay-config issue, not a bug
            # in the deliberation; log it once at a lower level.
            level = logging.DEBUG if is_ephemeral(event.kind) else logging.WARNING
            logger.log(level, "Buzz mirror could not publish %s: %s", description, exc)
            return False
        except Exception as exc:  # noqa: BLE001 - the mirror is always best-effort
            self.stats["failed"] += 1
            logger.warning("Buzz mirror failed on %s: %s", description, exc)
            return False

    def _spawn(self, coro: Awaitable) -> None:
        """Run a mirror coroutine detached, keeping a reference so it isn't GC'd."""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            logger.debug("No running loop; dropping Buzz mirror work")
            close = getattr(coro, "close", None)
            if close:  # avoid an "never awaited" warning on the dropped coroutine
                close()
            return
        task = loop.create_task(coro)
        self._background.add(task)
        task.add_done_callback(self._background.discard)

    # --- channels and agents ---

    async def ensure_channel(
        self, channel_id: str, name: str, about: str = "", visibility: str = "private"
    ) -> None:
        """Create the Buzz channel backing a subreddit. Idempotent locally.

        The channel id *is* the Colloquip subreddit id, which keeps the two
        systems joinable without a mapping table. A relay that already has the
        channel rejects the duplicate ``kind:9007``; that is expected and the
        failure is swallowed.
        """
        if channel_id in self._channels:
            return
        self._channels.add(channel_id)

        event = build_event(
            kind=KIND_CREATE_GROUP,
            content=about,
            keypair=self._service,
            tags=[
                channel_tag(channel_id),
                ["name", name],
                ["about", _truncate(about, 2000)],
                ["visibility", visibility],
                ["channel_type", "colloquip-community"],
            ],
        )
        await self._publish(event, f"channel create for '{name}'")

    async def announce_agent(self, agent_id: str, display_name: str, about: str = "") -> None:
        """Publish a ``kind:0`` profile so Buzz clients show names, not hex."""
        if agent_id in self._announced_agents:
            return
        self._announced_agents.add(agent_id)

        keypair = self.agent_keypair(agent_id)
        profile = {
            "name": agent_id,
            "display_name": display_name,
            "about": _truncate(about, 2000),
            "bot": True,
            "colloquip_agent_id": agent_id,
        }
        event = build_json_event(KIND_PROFILE, profile, keypair)
        await self._publish(event, f"profile for agent '{agent_id}'")

    async def add_agent_to_channel(self, channel_id: str, agent_id: str) -> None:
        """Add an agent to a channel as a member (``kind:9000``)."""
        event = build_event(
            kind=KIND_ADD_USER,
            content="",
            keypair=self._service,
            tags=[channel_tag(channel_id), ["p", self.agent_pubkey(agent_id)]],
        )
        await self._publish(event, f"add agent '{agent_id}' to channel")

    async def register_community(
        self,
        subreddit_id: str,
        name: str,
        description: str,
        agents: Optional[List[Dict[str, str]]] = None,
    ) -> None:
        """Mirror a whole subreddit: channel, agent profiles, memberships."""
        await self.ensure_channel(subreddit_id, name, description)
        for agent in agents or []:
            agent_id = agent["agent_id"]
            await self.announce_agent(
                agent_id, agent.get("display_name", agent_id), agent.get("about", "")
            )
            await self.add_agent_to_channel(subreddit_id, agent_id)

    # --- threads ---

    async def open_thread(
        self,
        session_id: str,
        channel_id: str,
        title: str,
        hypothesis: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """Announce a new deliberation and record its NIP-10 thread root."""
        await self.ensure_channel(channel_id, channel_id)

        prose = f"**{title}**\n\n> {hypothesis}\n\n_Deliberation {session_id} starting._"
        announcement = build_event(
            kind=KIND_CHAT,
            content=_truncate(prose),
            keypair=self._service,
            tags=[channel_tag(channel_id), ["colloquip_session", session_id]],
        )
        published = await self._publish(announcement, f"thread announcement for {session_id}")
        root_id = announcement.id if published else None
        self._threads[session_id] = (channel_id, root_id)

        payload = {
            "session_id": session_id,
            "title": title,
            "hypothesis": hypothesis,
            **(metadata or {}),
        }
        tags = [channel_tag(channel_id), ["colloquip_session", session_id]]
        if root_id:
            tags.append(root_tag(root_id))
        await self._publish(
            build_json_event(KIND_COLLOQUIP_THREAD, payload, self._service, tags=tags),
            f"thread metadata for {session_id}",
        )
        return root_id

    def _thread_tags(self, session_id: str, extra: Optional[List[List[str]]] = None):
        """Channel + NIP-10 root tags for an event belonging to a session."""
        channel_id, root_id = self._threads.get(session_id, (None, None))
        if channel_id is None:
            return None
        tags: List[List[str]] = [channel_tag(channel_id), ["colloquip_session", session_id]]
        if root_id:
            tags.append(root_tag(root_id))
        tags.extend(extra or [])
        return tags

    # --- the main hook ---

    async def mirror_event(self, session_id: Any, event: Dict[str, Any]) -> None:
        """Mirror one ``SessionManager._broadcast`` event to the relay.

        Accepts the broadcast dict verbatim — ``{"type": ..., "data": ...}`` —
        so the call site stays a single line and no new event type has to be
        threaded through the engine.
        """
        session_key = str(session_id)
        event_type = event.get("type")
        if event_type not in EVENT_TYPE_TO_KIND:
            return
        kind = EVENT_TYPE_TO_KIND[event_type]
        if kind is None:
            return
        if kind == KIND_COLLOQUIP_ENERGY and not self._publish_energy:
            return

        data = event.get("data") or {}
        tags = self._thread_tags(session_key)
        if tags is None:
            logger.debug("No Buzz thread for session %s; skipping %s", session_key, event_type)
            return

        if event_type == "post":
            await self._mirror_post(session_key, data, tags)
            return

        prose = self._prose_for(event_type, data)
        if prose and self._publish_prose:
            chat = build_event(
                kind=KIND_CHAT, content=_truncate(prose), keypair=self._service, tags=list(tags)
            )
            if await self._publish(chat, f"{event_type} note") and chat.id:
                tags = list(tags) + [["e", chat.id]]

        await self._publish(
            build_json_event(kind, data, self._service, tags=list(tags)),
            f"{event_type} payload",
        )

    async def _mirror_post(
        self, session_key: str, data: Dict[str, Any], tags: List[List[str]]
    ) -> None:
        """Publish an agent post: readable prose plus the structured payload."""
        agent_id = data.get("agent_id", "unknown")
        keypair = self.agent_keypair(agent_id)
        post_tags = list(tags) + [
            ["colloquip_stance", str(data.get("stance", ""))],
            ["colloquip_phase", str(data.get("phase", ""))],
        ]

        chat_id: Optional[str] = None
        if self._publish_prose:
            chat = build_event(
                kind=KIND_CHAT,
                content=_truncate(str(data.get("content", ""))),
                keypair=keypair,
                tags=list(post_tags),
            )
            if await self._publish(chat, f"post by {agent_id}"):
                chat_id = chat.id

        payload_tags = list(post_tags)
        if chat_id:
            payload_tags.append(["e", chat_id])
        await self._publish(
            build_json_event(EVENT_TYPE_TO_KIND["post"], data, keypair, tags=payload_tags),
            f"post payload by {agent_id}",
        )

    @staticmethod
    def _prose_for(event_type: str, data: Dict[str, Any]) -> Optional[str]:
        """Render a human-readable note for non-post events, if worth one."""
        if event_type == "phase_change":
            phase = data.get("current_phase", "?")
            confidence = data.get("confidence")
            suffix = f" (confidence {confidence:.0%})" if isinstance(confidence, float) else ""
            observation = data.get("observation")
            note = f"_Phase → **{phase}**{suffix}_"
            return f"{note}\n{observation}" if observation else note

        if event_type == "budget_skip":
            return (
                f"_{data.get('agent_id', 'an agent')} was skipped: "
                f"{data.get('reason', 'budget exhausted')}_"
            )

        if event_type == "session_complete":
            lines = [f"**Synthesis**\n\n{data.get('summary', '')}"]
            for label, key in (
                ("Agreements", "agreements"),
                ("Disagreements", "disagreements"),
                ("Minority positions", "minority_positions"),
            ):
                items = data.get(key) or []
                if items:
                    rendered = "\n".join(f"- {item}" for item in items)
                    lines.append(f"\n**{label}**\n{rendered}")
            return "\n".join(lines)

        # Energy ticks are telemetry; they would drown the channel as prose.
        return None

    # --- inbound: humans talking back ---

    async def watch_channel(
        self,
        channel_id: str,
        on_message: Optional[Callable[[str, str, NostrEvent], Awaitable[None]]] = None,
        on_reaction: Optional[Callable[[str, str, NostrEvent], Awaitable[None]]] = None,
    ) -> None:
        """Route human messages and reactions in a channel back into Colloquip.

        Events authored by Colloquip's own keys are ignored — otherwise the
        mirror would feed its own posts back in as interventions. Historical
        events are skipped so a reconnect never replays old messages as new
        ones.
        """
        kinds = [k for k, cb in ((KIND_CHAT, on_message), (KIND_REACTION, on_reaction)) if cb]
        if not kinds:
            return
        filters = [{"kinds": kinds, "#h": [channel_id]}]

        try:
            async for event in self._client.subscribe(filters, include_historical=False):
                if self.is_own_pubkey(event.pubkey):
                    continue
                self.stats["received"] += 1
                session_id = event.tag_value("colloquip_session") or self._session_for_event(event)
                if session_id is None:
                    logger.debug("Ignoring Buzz event %s: no session context", (event.id or "")[:8])
                    continue
                try:
                    if event.kind == KIND_CHAT and on_message:
                        await on_message(session_id, event.content, event)
                    elif event.kind == KIND_REACTION and on_reaction:
                        await on_reaction(session_id, event.content, event)
                except Exception:  # noqa: BLE001 - one bad handler must not kill the watcher
                    logger.exception("Buzz inbound handler failed for %s", (event.id or "")[:8])
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001
            logger.warning("Buzz channel watcher for %s stopped: %s", channel_id, exc)

    def _session_for_event(self, event: NostrEvent) -> Optional[str]:
        """Resolve an inbound event to a session via its NIP-10 root tag."""
        referenced = set(event.tag_values("e"))
        for session_id, (_, root_id) in self._threads.items():
            if root_id and root_id in referenced:
                return session_id
        return None

    def start_watching(self, channel_id: str, **handlers: Any) -> None:
        """Start a background watcher for a channel."""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            logger.debug("No running loop; not watching Buzz channel %s", channel_id)
            return
        task = loop.create_task(self.watch_channel(channel_id, **handlers))
        self._watchers.append(task)

    # --- fire-and-forget entry points for synchronous call sites ---

    def mirror_event_nowait(self, session_id: Any, event: Dict[str, Any]) -> None:
        self._spawn(self.mirror_event(session_id, event))

    def open_thread_nowait(self, *args: Any, **kwargs: Any) -> None:
        self._spawn(self.open_thread(*args, **kwargs))

    def register_community_nowait(self, *args: Any, **kwargs: Any) -> None:
        self._spawn(self.register_community(*args, **kwargs))

    # --- lifecycle ---

    async def close(self) -> None:
        """Cancel watchers, drain in-flight publishes, close the connection."""
        for task in self._watchers:
            task.cancel()
        for task in list(self._background):
            task.cancel()
        pending = [*self._watchers, *self._background]
        if pending:
            await asyncio.gather(*pending, return_exceptions=True)
        self._watchers.clear()
        self._background.clear()
        await self._client.close()

    def describe(self) -> Dict[str, Any]:
        """Operational snapshot for the health endpoint."""
        return {
            "service_pubkey": self._service.public_hex,
            "service_npub": self._service.npub,
            "channels": sorted(self._channels),
            "threads": len(self._threads),
            "agents": sorted(self._agent_keys),
            "stats": dict(self.stats),
        }


def parse_intervention_type(content: str) -> tuple[str, str]:
    """Map a human's Buzz message to a ``HumanIntervention`` type.

    A leading ``!command`` picks the type explicitly (mirroring Buzz's own
    ``!shutdown`` convention for agent control); anything else is a question,
    which is the safe default because it injects energy without redirecting
    the deliberation.
    """
    stripped = content.strip()
    commands = {
        "!question": "question",
        "!data": "data",
        "!redirect": "redirect",
        "!terminate": "terminate",
        "!stop": "terminate",
    }
    for command, kind in commands.items():
        if stripped.lower().startswith(command):
            remainder = stripped[len(command) :].strip()
            return kind, remainder or stripped
    return "question", stripped


def json_content(event: NostrEvent) -> Optional[Dict[str, Any]]:
    """Parse a Colloquip event's JSON payload, or ``None`` if it isn't JSON."""
    try:
        parsed = json.loads(event.content)
    except (json.JSONDecodeError, TypeError):
        return None
    return parsed if isinstance(parsed, dict) else None
