"""Buzz adapter — mirror Colloquip deliberations onto a Buzz relay.

Buzz (https://github.com/block/buzz) is a self-hosted Nostr relay where humans
and agents share channels, each with their own keypair and an audit trail.
This package projects Colloquip onto that substrate without moving Colloquip's
system of record: Postgres stays authoritative, and the relay gets a signed,
auditable mirror that Buzz's desktop and mobile clients can read, search, and
reply to.

Enable it with ``BUZZ_ENABLED=true`` plus ``BUZZ_RELAY_URL``,
``BUZZ_PRIVATE_KEY``, and ``BUZZ_AGENT_KEY_SEED``. Unset, every hook is a
no-op. See ``docs/buzz_adapter.md``.
"""

from colloquip.buzz.client import BuzzRelayClient, RecordingRelayClient, RelayError
from colloquip.buzz.config import BuzzSettings, create_mirror, load_buzz_settings
from colloquip.buzz.events import NostrEvent, build_event, build_json_event
from colloquip.buzz.keys import BuzzKeypair, derive_agent_keypair, keypair_from_private
from colloquip.buzz.mirror import BuzzMirror, parse_intervention_type

__all__ = [
    "BuzzKeypair",
    "BuzzMirror",
    "BuzzRelayClient",
    "BuzzSettings",
    "NostrEvent",
    "RecordingRelayClient",
    "RelayError",
    "build_event",
    "build_json_event",
    "create_mirror",
    "derive_agent_keypair",
    "keypair_from_private",
    "load_buzz_settings",
    "parse_intervention_type",
]
