"""Webhook watcher: receives events via HTTP POST.

Unlike polling watchers, the webhook watcher doesn't poll — it receives
events pushed to it via an API endpoint. It validates and transforms
incoming payloads into WatcherEvent objects.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from colloquip.models import WatcherConfig, WatcherEvent, WatcherSource
from colloquip.watchers.interface import BaseWatcher

logger = logging.getLogger(__name__)


class WebhookWatcher(BaseWatcher):
    """Receives events from external systems via webhook.

    Events are pushed in via receive_webhook(), not polled.
    The poll() method returns any buffered events and clears the buffer.

    Config options (in config.config):
        secret: Optional shared secret for payload validation
        allowed_senders: Optional list of allowed sender identifiers
    """

    def __init__(self, config: WatcherConfig):
        super().__init__(config)
        self._buffer: List[WatcherEvent] = []
        self._secret: Optional[str] = config.config.get("secret")
        self._allowed_senders: Optional[List[str]] = config.config.get("allowed_senders")

    async def poll(self) -> List[WatcherEvent]:
        """Return buffered webhook events and clear the buffer."""
        events = list(self._buffer)
        self._buffer.clear()
        return events

    def receive_webhook(
        self,
        payload: Dict[str, Any],
        sender: Optional[str] = None,
    ) -> Optional[WatcherEvent]:
        """Receive and validate a webhook payload.

        Args:
            payload: The webhook payload (must contain 'title')
            sender: Optional sender identifier for access control

        Returns:
            The created WatcherEvent, or None if validation fails
        """
        # Validate sender
        if self._allowed_senders is not None:
            if sender not in self._allowed_senders:
                logger.warning(
                    "Webhook %s rejected payload from unauthorized sender: %s",
                    self.config.name, sender,
                )
                return None

        # Validate payload
        title = payload.get("title")
        if not title:
            logger.warning("Webhook %s received payload without title", self.config.name)
            return None

        event = WatcherEvent(
            watcher_id=self.watcher_id,
            subreddit_id=self.subreddit_id,
            title=str(title),
            summary=str(payload.get("summary", "")),
            source=WatcherSource(
                source_type="webhook",
                source_id=sender or "unknown",
                url=payload.get("url"),
                metadata={
                    k: v for k, v in payload.items()
                    if k not in ("title", "summary", "url")
                },
            ),
            raw_data=payload,
        )

        self._buffer.append(event)
        logger.info("Webhook %s received event: %s", self.config.name, title)
        return event

    async def validate_config(self) -> bool:
        """Webhook watchers are always valid — they just receive data."""
        return True

    @property
    def buffer_size(self) -> int:
        return len(self._buffer)
