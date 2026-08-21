"""Nostr event construction, serialization, and signing (NIP-01).

An event id is the SHA-256 of a canonical JSON array::

    [0, <pubkey>, <created_at>, <kind>, <tags>, <content>]

serialized with no whitespace and UTF-8 escapes exactly as NIP-01 specifies.
Get the serialization wrong and the relay rejects the event with an opaque
``invalid: bad id``, so the encoding rules live in one place here.
"""

import json
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from colloquip.buzz.keys import BuzzKeypair
from colloquip.buzz.schnorr import schnorr_verify

Tag = List[str]


def _canonical_json(value: Any) -> str:
    """Serialize exactly as NIP-01 requires: no whitespace, no ASCII escaping."""
    return json.dumps(value, separators=(",", ":"), ensure_ascii=False)


@dataclass
class NostrEvent:
    """A Nostr event, signed or not."""

    kind: int
    content: str
    pubkey: str
    tags: List[Tag] = field(default_factory=list)
    created_at: int = field(default_factory=lambda: int(time.time()))
    id: Optional[str] = None
    sig: Optional[str] = None

    def serialize(self) -> str:
        """Return the canonical pre-image whose SHA-256 is the event id."""
        return _canonical_json(
            [0, self.pubkey, self.created_at, self.kind, self.tags, self.content]
        )

    def compute_id(self) -> str:
        import hashlib

        return hashlib.sha256(self.serialize().encode("utf-8")).hexdigest()

    def sign(self, keypair: BuzzKeypair, aux_rand: bytes = b"\x00" * 32) -> "NostrEvent":
        """Compute the id and attach a signature. Mutates and returns self."""
        if keypair.public_hex != self.pubkey:
            raise ValueError(
                f"keypair {keypair.public_hex[:8]}… cannot sign an event "
                f"authored by {self.pubkey[:8]}…"
            )
        self.id = self.compute_id()
        self.sig = keypair.sign(bytes.fromhex(self.id), aux_rand)
        return self

    def verify(self) -> bool:
        """Check that the id matches the content and the signature is valid."""
        if not self.id or not self.sig:
            return False
        if self.id != self.compute_id():
            return False
        try:
            return schnorr_verify(
                bytes.fromhex(self.id), bytes.fromhex(self.pubkey), bytes.fromhex(self.sig)
            )
        except ValueError:
            return False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "pubkey": self.pubkey,
            "created_at": self.created_at,
            "kind": self.kind,
            "tags": self.tags,
            "content": self.content,
            "sig": self.sig,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "NostrEvent":
        return cls(
            kind=data["kind"],
            content=data.get("content", ""),
            pubkey=data["pubkey"],
            tags=[list(t) for t in data.get("tags", [])],
            created_at=data.get("created_at", 0),
            id=data.get("id"),
            sig=data.get("sig"),
        )

    # --- tag helpers ---

    def tag_value(self, name: str) -> Optional[str]:
        """First value of the first tag with this name, if any."""
        for tag in self.tags:
            if len(tag) >= 2 and tag[0] == name:
                return tag[1]
        return None

    def tag_values(self, name: str) -> List[str]:
        """All values across every tag with this name."""
        return [tag[1] for tag in self.tags if len(tag) >= 2 and tag[0] == name]

    @property
    def channel(self) -> Optional[str]:
        """The Buzz channel this event is scoped to (its ``#h`` tag)."""
        return self.tag_value("h")


def build_event(
    kind: int,
    content: str,
    keypair: BuzzKeypair,
    tags: Optional[List[Tag]] = None,
    created_at: Optional[int] = None,
    aux_rand: bytes = b"\x00" * 32,
) -> NostrEvent:
    """Build and sign an event in one step."""
    event = NostrEvent(
        kind=kind,
        content=content,
        pubkey=keypair.public_hex,
        tags=tags or [],
        created_at=created_at if created_at is not None else int(time.time()),
    )
    return event.sign(keypair, aux_rand)


def build_json_event(
    kind: int,
    payload: Any,
    keypair: BuzzKeypair,
    tags: Optional[List[Tag]] = None,
    created_at: Optional[int] = None,
    aux_rand: bytes = b"\x00" * 32,
) -> NostrEvent:
    """Build a signed event whose content is a canonical JSON payload."""
    return build_event(
        kind=kind,
        content=_canonical_json(payload),
        keypair=keypair,
        tags=tags,
        created_at=created_at,
        aux_rand=aux_rand,
    )


def channel_tag(channel_id: str) -> Tag:
    """The ``#h`` tag every channel-scoped Buzz event must carry."""
    return ["h", channel_id]


def reply_tag(parent_event_id: str, relay: str = "") -> Tag:
    """A NIP-10 reply marker pointing at the thread parent."""
    return ["e", parent_event_id, relay, "reply"]


def root_tag(root_event_id: str, relay: str = "") -> Tag:
    """A NIP-10 root marker pointing at the thread root."""
    return ["e", root_event_id, relay, "root"]
