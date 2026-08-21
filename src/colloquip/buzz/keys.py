"""Keypair management for Buzz-mirrored Colloquip identities.

Every Colloquip participant that publishes to Buzz needs a secp256k1 keypair:

* the **service key** (``BUZZ_PRIVATE_KEY``) signs platform-level events —
  channel creation, membership, phase/energy telemetry;
* each **agent** gets its own key so posts carry the agent's identity and the
  relay's audit chain attributes them individually, exactly as Buzz intends.

Agent keys are *derived*, not stored: ``HMAC-SHA256(seed, agent_id)`` reduced
mod n. One secret (``BUZZ_AGENT_KEY_SEED``) therefore reproduces the whole
agent roster on any deployment, which keeps agent identities stable across
restarts without adding a key table or a secrets backend. Rotating the seed
rotates every agent identity, so treat it as long-lived.
"""

import hashlib
import hmac
from dataclasses import dataclass

from colloquip.buzz.bech32 import Bech32Error, from_npub, from_nsec, to_npub, to_nsec
from colloquip.buzz.schnorr import N, SchnorrError, pubkey_from_privkey, schnorr_sign


@dataclass(frozen=True)
class BuzzKeypair:
    """A secp256k1 keypair in the form Nostr uses (x-only public key)."""

    private_hex: str
    public_hex: str

    @property
    def npub(self) -> str:
        return to_npub(self.public_hex)

    @property
    def nsec(self) -> str:
        return to_nsec(self.private_hex)

    def sign(self, digest: bytes, aux_rand: bytes = b"\x00" * 32) -> str:
        """Sign a 32-byte digest, returning a 64-byte hex signature."""
        return schnorr_sign(digest, bytes.fromhex(self.private_hex), aux_rand).hex()

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        # Never render the private half; these objects end up in log lines.
        return f"BuzzKeypair(public_hex='{self.public_hex}')"


def keypair_from_private(private_key: str) -> BuzzKeypair:
    """Build a keypair from a hex or ``nsec1...`` private key."""
    private_key = private_key.strip()
    if private_key.startswith("nsec1"):
        private_hex = from_nsec(private_key)
    else:
        private_hex = private_key.lower().removeprefix("0x")

    try:
        raw = bytes.fromhex(private_hex)
    except ValueError:
        raise SchnorrError("private key is not valid hex") from None
    if len(raw) != 32:
        raise SchnorrError(f"private key must be 32 bytes, got {len(raw)}")

    return BuzzKeypair(private_hex=private_hex, public_hex=pubkey_from_privkey(raw).hex())


def derive_agent_keypair(seed: str, agent_id: str) -> BuzzKeypair:
    """Deterministically derive an agent's keypair from a master seed.

    The derivation is ``HMAC-SHA256(seed, "colloquip-agent:" + agent_id)``
    reduced mod n. The counter loop guards the (vanishingly improbable) case
    where the reduction lands on zero.
    """
    if not seed:
        raise SchnorrError("agent key seed must not be empty")

    counter = 0
    while counter < 256:
        message = f"colloquip-agent:{agent_id}".encode()
        if counter:
            message += b":" + str(counter).encode()
        digest = hmac.new(seed.encode(), message, hashlib.sha256).digest()
        scalar = int.from_bytes(digest, "big") % N
        if scalar != 0:
            private_hex = scalar.to_bytes(32, "big").hex()
            return BuzzKeypair(
                private_hex=private_hex,
                public_hex=pubkey_from_privkey(bytes.fromhex(private_hex)).hex(),
            )
        counter += 1
    raise SchnorrError(f"could not derive a usable key for agent '{agent_id}'")


def normalize_pubkey(pubkey: str) -> str:
    """Accept hex or ``npub1...`` and return lowercase 32-byte hex."""
    pubkey = pubkey.strip()
    if pubkey.startswith("npub1"):
        return from_npub(pubkey)
    pubkey = pubkey.lower().removeprefix("0x")
    if len(pubkey) != 64:
        raise Bech32Error(f"pubkey must be 64 hex characters, got {len(pubkey)}")
    bytes.fromhex(pubkey)  # raises ValueError if not hex
    return pubkey
