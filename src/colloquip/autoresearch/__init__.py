"""Autoresearch capability layer — autonomous research loops for any agent.

Inspired by Karpathy's autoresearch:
- Three-file pattern: immutable prep (AgentDependencies), mutable work file
  (scratchpad), directive (subreddit mission + persona)
- Fixed-budget iteration (max_steps / max_tokens / wallclock)
- Metric-driven commit-or-reset of findings

The loop is invoked from inside ``BaseDeliberationAgent.generate_post`` when
the agent is configured with ``autoresearch_enabled=True``. It reuses the
shared :class:`~colloquip.tools.registry.ToolRegistry` to execute search /
read actions, and emits an :class:`~colloquip.models.AutoresearchRun` audit
record that the engine can persist.
"""

from colloquip.autoresearch.loop import AutoresearchLoop, MockAutoresearchLoop
from colloquip.autoresearch.metrics import (
    CitationDensityMetric,
    CoverageMetric,
    NoveltyGainMetric,
)

__all__ = [
    "AutoresearchLoop",
    "MockAutoresearchLoop",
    "NoveltyGainMetric",
    "CoverageMetric",
    "CitationDensityMetric",
]
