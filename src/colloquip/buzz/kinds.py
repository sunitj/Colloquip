"""Nostr event kinds used by the Buzz adapter.

Two groups:

**Buzz / NIP kinds** — understood by the relay and rendered by every Buzz
client. Colloquip posts go out as ``kind:9`` group chat so a human reading the
channel in the Buzz desktop app sees a normal, readable conversation.

**Colloquip kinds** — the structured payload behind each post (stance, novelty,
claims, citations) plus deliberation telemetry. Buzz's ARCHITECTURE.md reserves
40000–49999 for client-defined kinds that the relay routes and unknown clients
ignore; 40002/40003 are already taken by Buzz's own rich-content and edit
events, so Colloquip sits at 41000+.

Energy updates fire on every turn and are worthless once stale, so they use an
*ephemeral* kind (20000–29999), which the relay fans out via Redis without
writing to Postgres. A relay that does not recognise the kind will reject it;
the mirror treats publish failures as non-fatal for exactly this reason.
"""

# --- Nostr / Buzz kinds ---
KIND_PROFILE = 0
KIND_DELETE = 5
KIND_REACTION = 7
KIND_CHAT = 9
KIND_AUTH = 22242  # NIP-42 client authentication
KIND_ADD_USER = 9000
KIND_REMOVE_USER = 9001
KIND_EDIT_METADATA = 9002
KIND_CREATE_GROUP = 9007
KIND_PRESENCE = 20001

# --- Colloquip kinds (persisted) ---
KIND_COLLOQUIP_POST = 41000
KIND_COLLOQUIP_PHASE = 41001
KIND_COLLOQUIP_CONSENSUS = 41002
KIND_COLLOQUIP_BUDGET_SKIP = 41003
KIND_COLLOQUIP_THREAD = 41004
KIND_COLLOQUIP_APPROVAL = 41005

# --- Colloquip kinds (ephemeral, Redis-only) ---
KIND_COLLOQUIP_ENERGY = 20100

#: Maps a ``SessionManager._broadcast`` event type to its Colloquip kind.
#: ``None`` means the event is deliberately not mirrored.
EVENT_TYPE_TO_KIND = {
    "post": KIND_COLLOQUIP_POST,
    "phase_change": KIND_COLLOQUIP_PHASE,
    "energy_update": KIND_COLLOQUIP_ENERGY,
    "budget_skip": KIND_COLLOQUIP_BUDGET_SKIP,
    "session_complete": KIND_COLLOQUIP_CONSENSUS,
    "done": None,
    "error": None,
}


def is_ephemeral(kind: int) -> bool:
    """Ephemeral kinds are relayed but never stored (NIP-01 20000–29999)."""
    return 20000 <= kind < 30000
