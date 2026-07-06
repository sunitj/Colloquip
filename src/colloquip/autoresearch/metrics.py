"""Metric implementations for the autoresearch loop.

Metrics score the *state of the scratchpad* — not a single step — so the loop
can compare before/after and decide whether a step committed useful findings.

The default, ``NoveltyGainMetric``, is intentionally cheap: it measures
token-overlap novelty. Callers that want semantic novelty can inject a
different metric through ``AutoresearchConfig.metric`` at run time.
"""

from __future__ import annotations

import re
from typing import Iterable, Set

_WORD_RE = re.compile(r"[a-zA-Z][a-zA-Z0-9_-]{2,}")


def _tokenize(text: str) -> Set[str]:
    return {m.group(0).lower() for m in _WORD_RE.finditer(text or "")}


class AutoresearchMetric:
    """Base class for scratchpad-level metrics."""

    name: str = "noop"

    def evaluate(self, previous: str, current: str) -> float:
        """Return the metric value for ``current`` given the ``previous`` state.

        Subclasses override this. The default returns zero so a missing
        implementation is a no-op (not a crash).
        """
        return 0.0

    def delta(self, previous: str, current: str) -> float:
        """Return the metric gain from ``previous`` to ``current``."""
        return self.evaluate(previous, current) - self.evaluate("", previous)


class NoveltyGainMetric(AutoresearchMetric):
    """Token-overlap-based novelty gain.

    Computes the fraction of unique tokens in ``current`` that are not
    present in ``previous``. Cheap and deterministic — good enough as the
    default "did this step add anything new?" signal.
    """

    name = "novelty_gain"

    def evaluate(self, previous: str, current: str) -> float:
        prev_tokens = _tokenize(previous)
        curr_tokens = _tokenize(current)
        if not curr_tokens:
            return 0.0
        new_tokens = curr_tokens - prev_tokens
        return len(new_tokens) / max(len(curr_tokens), 1)

    def delta(self, previous: str, current: str) -> float:
        if not current:
            return 0.0
        prev_tokens = _tokenize(previous)
        curr_tokens = _tokenize(current)
        if not curr_tokens:
            return 0.0
        new_tokens = curr_tokens - prev_tokens
        # Reward adding new tokens proportional to total knowledge
        return len(new_tokens) / max(len(prev_tokens) + len(new_tokens), 1)


class CoverageMetric(AutoresearchMetric):
    """Breadth metric: how many distinct topic tokens the scratchpad covers."""

    name = "coverage"

    def __init__(self, target_tokens: Iterable[str] | None = None):
        self._target = {t.lower() for t in (target_tokens or [])}

    def evaluate(self, previous: str, current: str) -> float:
        if not self._target:
            # Fall back to raw unique token count (scaled)
            return min(len(_tokenize(current)) / 200.0, 1.0)
        hits = _tokenize(current) & self._target
        return len(hits) / max(len(self._target), 1)


class CitationDensityMetric(AutoresearchMetric):
    """Counts citation-like tokens in the scratchpad (e.g. ``[PUBMED:...]``)."""

    name = "citation_density"

    _CITE_RE = re.compile(r"\[(?:PUBMED|PMID|DOI|WEB):[^\]]+\]")

    def evaluate(self, previous: str, current: str) -> float:
        hits = self._CITE_RE.findall(current or "")
        # Normalize to a 0..1-ish range by capping at 20 citations
        return min(len(hits) / 20.0, 1.0)


_METRIC_REGISTRY = {
    NoveltyGainMetric.name: NoveltyGainMetric,
    CoverageMetric.name: CoverageMetric,
    CitationDensityMetric.name: CitationDensityMetric,
}


def get_metric(name: str) -> AutoresearchMetric:
    """Return a metric instance by name, defaulting to NoveltyGainMetric."""
    cls = _METRIC_REGISTRY.get(name, NoveltyGainMetric)
    return cls()
