"""Configuration and construction for the Buzz adapter.

The adapter is off unless ``BUZZ_ENABLED=true`` *and* a relay URL is set, so a
deployment that has never heard of Buzz behaves exactly as before.
"""

import logging
import os
from typing import Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class BuzzSettings(BaseModel):
    """Environment-driven settings for mirroring to a Buzz relay."""

    enabled: bool = False
    relay_url: str = ""
    #: Service key (hex or ``nsec1...``) that signs platform-level events.
    private_key: str = ""
    #: Master seed from which every agent's keypair is derived.
    agent_key_seed: str = ""
    #: Mirror per-turn energy as ephemeral events.
    publish_energy: bool = True
    #: Also publish human-readable ``kind:9`` chat alongside structured payloads.
    publish_prose: bool = True
    #: Accept human messages in Buzz channels as deliberation interventions.
    accept_interventions: bool = True
    connect_timeout: float = Field(default=10.0, gt=0)
    publish_timeout: float = Field(default=10.0, gt=0)

    @property
    def configured(self) -> bool:
        """True when the adapter has everything it needs to connect."""
        return bool(self.enabled and self.relay_url and self.private_key and self.agent_key_seed)


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


def load_buzz_settings() -> BuzzSettings:
    """Load Buzz settings from the environment."""
    return BuzzSettings(
        enabled=_env_bool("BUZZ_ENABLED", False),
        relay_url=os.environ.get("BUZZ_RELAY_URL", ""),
        private_key=os.environ.get("BUZZ_PRIVATE_KEY", ""),
        agent_key_seed=os.environ.get("BUZZ_AGENT_KEY_SEED", ""),
        publish_energy=_env_bool("BUZZ_PUBLISH_ENERGY", True),
        publish_prose=_env_bool("BUZZ_PUBLISH_PROSE", True),
        accept_interventions=_env_bool("BUZZ_ACCEPT_INTERVENTIONS", True),
        connect_timeout=float(os.environ.get("BUZZ_CONNECT_TIMEOUT", "10")),
        publish_timeout=float(os.environ.get("BUZZ_PUBLISH_TIMEOUT", "10")),
    )


def create_mirror(settings: Optional[BuzzSettings] = None):
    """Build a ``BuzzMirror`` from settings, or ``None`` when not configured.

    Returning ``None`` rather than raising is deliberate: a missing or
    malformed Buzz configuration must never stop Colloquip from booting.
    """
    from colloquip.buzz.client import BuzzRelayClient
    from colloquip.buzz.keys import keypair_from_private
    from colloquip.buzz.mirror import BuzzMirror

    settings = settings or load_buzz_settings()

    if not settings.enabled:
        return None
    if not settings.configured:
        missing = [
            name
            for name, value in (
                ("BUZZ_RELAY_URL", settings.relay_url),
                ("BUZZ_PRIVATE_KEY", settings.private_key),
                ("BUZZ_AGENT_KEY_SEED", settings.agent_key_seed),
            )
            if not value
        ]
        logger.warning("BUZZ_ENABLED is set but %s missing; mirror disabled", ", ".join(missing))
        return None

    try:
        service_keypair = keypair_from_private(settings.private_key)
    except Exception as exc:  # noqa: BLE001
        logger.error("Invalid BUZZ_PRIVATE_KEY; Buzz mirror disabled: %s", exc)
        return None

    client = BuzzRelayClient(
        settings.relay_url,
        service_keypair,
        connect_timeout=settings.connect_timeout,
        publish_timeout=settings.publish_timeout,
    )
    logger.info(
        "Buzz mirror enabled: relay=%s service=%s",
        settings.relay_url,
        service_keypair.npub,
    )
    return BuzzMirror(
        client,
        service_keypair,
        settings.agent_key_seed,
        publish_energy=settings.publish_energy,
        publish_prose=settings.publish_prose,
    )
