"""Literature watcher: monitors PubMed for new papers matching a query.

Reuses the PubMed tool's search infrastructure to detect new publications.
Tracks last-checked state to return only genuinely new results.
"""

import logging
from datetime import datetime, timezone
from typing import List, Set
from uuid import uuid4

from colloquip.models import WatcherConfig, WatcherEvent, WatcherSource
from colloquip.watchers.interface import BaseWatcher

logger = logging.getLogger(__name__)


class LiteratureWatcher(BaseWatcher):
    """Monitors PubMed for new papers matching a configured query.

    Uses NCBI E-utilities (same as PubMedTool) to check for new papers.
    Tracks seen PMIDs to avoid duplicate events.
    """

    def __init__(self, config: WatcherConfig, pubmed_tool=None):
        super().__init__(config)
        self._pubmed_tool = pubmed_tool
        self._seen_pmids: Set[str] = set()
        self._last_checked: datetime | None = None
        self._max_results = config.config.get("max_results", 10)

    async def poll(self) -> List[WatcherEvent]:
        """Poll PubMed for new papers matching the query."""
        if not self.config.query:
            logger.debug("Watcher %s has no query configured", self.config.name)
            return []

        if self._pubmed_tool is None:
            logger.warning("No PubMed tool available for watcher %s", self.config.name)
            return []

        try:
            result = await self._pubmed_tool.execute(
                query=self.config.query,
                max_results=self._max_results,
            )
        except Exception as e:
            logger.error("PubMed search failed for watcher %s: %s", self.config.name, e)
            return []

        if result is None or result.error:
            logger.warning("PubMed search error: %s", getattr(result, "error", "None result"))
            return []

        events = []
        for sr in result.results:
            # Skip already-seen papers
            if sr.source_id and sr.source_id in self._seen_pmids:
                continue

            if sr.source_id:
                self._seen_pmids.add(sr.source_id)

            events.append(WatcherEvent(
                watcher_id=self.watcher_id,
                subreddit_id=self.subreddit_id,
                title=sr.title,
                summary=sr.abstract or sr.snippet or "",
                source=WatcherSource(
                    source_type="pubmed",
                    source_id=sr.source_id or "",
                    url=sr.url,
                    metadata={
                        "authors": sr.authors,
                        "year": sr.year,
                        "doi": sr.doi,
                    },
                ),
                raw_data={
                    "title": sr.title,
                    "authors": sr.authors,
                    "abstract": sr.abstract,
                    "year": sr.year,
                    "doi": sr.doi,
                    "source_id": sr.source_id,
                    "url": sr.url,
                },
            ))

        self._last_checked = datetime.now(timezone.utc)
        if events:
            logger.info(
                "Watcher %s found %d new papers", self.config.name, len(events)
            )
        return events

    async def validate_config(self) -> bool:
        """Check that the watcher has a query and PubMed tool."""
        if not self.config.query:
            return False
        if self._pubmed_tool is None:
            return False
        return True

    @property
    def seen_count(self) -> int:
        """Number of unique PMIDs seen."""
        return len(self._seen_pmids)

    @property
    def last_checked(self) -> datetime | None:
        return self._last_checked
