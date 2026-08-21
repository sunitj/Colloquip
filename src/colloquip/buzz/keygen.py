"""Generate keys for the Buzz adapter: ``python -m colloquip.buzz.keygen``.

Prints a service keypair and a random agent seed, plus the ``npub`` values an
operator needs to allowlist Colloquip on the relay. Also shows the derived
identity for any agent ids passed as arguments, so you can confirm which pubkey
will author which agent's posts before pointing it at a live relay.
"""

import os
import secrets
import sys

from colloquip.buzz.keys import derive_agent_keypair, keypair_from_private
from colloquip.buzz.schnorr import N


def _random_private_hex() -> str:
    while True:
        candidate = int.from_bytes(os.urandom(32), "big")
        if 1 <= candidate < N:
            return candidate.to_bytes(32, "big").hex()


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv

    service = keypair_from_private(_random_private_hex())
    seed = secrets.token_urlsafe(32)

    print("# Add to .env — treat both values as secrets.")
    print("BUZZ_ENABLED=true")
    print("BUZZ_RELAY_URL=ws://localhost:8080")
    print(f"BUZZ_PRIVATE_KEY={service.nsec}")
    print(f"BUZZ_AGENT_KEY_SEED={seed}")
    print()
    print(f"# Service identity (allowlist this on the relay):\n#   {service.npub}")

    if argv:
        print("\n# Derived agent identities:")
        for agent_id in argv:
            print(f"#   {agent_id:<20} {derive_agent_keypair(seed, agent_id).npub}")
    else:
        print("\n# Pass agent ids as arguments to preview their derived identities.")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
