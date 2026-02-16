"""Application metrics collection for Colloquip.

Provides Prometheus-compatible metrics for monitoring deliberation throughput,
cost, memory retrieval, watcher activity, and error rates.

Metrics are only collected when prometheus_client is installed.
"""

import logging
import time
from contextlib import contextmanager

logger = logging.getLogger(__name__)

try:
    from prometheus_client import Counter, Gauge, Histogram, generate_latest

    _PROMETHEUS_AVAILABLE = True
except ImportError:
    _PROMETHEUS_AVAILABLE = False

    # Stub classes for when prometheus_client is not installed
    class _NoOp:
        def inc(self, *a, **kw):
            pass

        def dec(self, *a, **kw):
            pass

        def set(self, *a, **kw):
            pass

        def observe(self, *a, **kw):
            pass

        def labels(self, **kw):
            return self

    def generate_latest() -> bytes:
        return b"# prometheus_client not installed\n"


def _counter(name, doc, labelnames=()):
    if _PROMETHEUS_AVAILABLE:
        return Counter(name, doc, labelnames=labelnames)
    return _NoOp()


def _histogram(name, doc, labelnames=(), buckets=None):
    if _PROMETHEUS_AVAILABLE:
        kw = {"labelnames": labelnames}
        if buckets:
            kw["buckets"] = buckets
        return Histogram(name, doc, **kw)
    return _NoOp()


def _gauge(name, doc, labelnames=()):
    if _PROMETHEUS_AVAILABLE:
        return Gauge(name, doc, labelnames=labelnames)
    return _NoOp()


# --- Deliberation metrics ---
deliberations_total = _counter(
    "colloquip_deliberations_total",
    "Total deliberations started",
)
deliberation_duration_seconds = _histogram(
    "colloquip_deliberation_duration_seconds",
    "Deliberation wall-clock time",
    buckets=[1, 5, 10, 30, 60, 120, 300, 600],
)
deliberation_cost_usd = _histogram(
    "colloquip_deliberation_cost_usd",
    "Cost per deliberation in USD",
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0],
)

# --- Memory metrics ---
memory_retrievals_total = _counter(
    "colloquip_memory_retrievals_total",
    "Memory retrieval requests",
)
memory_retrieval_latency_seconds = _histogram(
    "colloquip_memory_retrieval_latency_seconds",
    "Vector search latency",
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5],
)
memory_store_size = _gauge(
    "colloquip_memory_store_size",
    "Total memories stored",
)

# --- Watcher metrics ---
watcher_events_total = _counter(
    "colloquip_watcher_events_total",
    "Events detected by watchers",
    labelnames=["watcher_type"],
)
triage_decisions_total = _counter(
    "colloquip_triage_decisions_total",
    "Triage decisions by signal level",
    labelnames=["signal"],
)
notifications_total = _counter(
    "colloquip_notifications_total",
    "Notifications sent",
)

# --- LLM metrics ---
llm_tokens_total = _counter(
    "colloquip_llm_tokens_total",
    "LLM tokens used",
    labelnames=["model", "direction"],
)
llm_errors_total = _counter(
    "colloquip_llm_errors_total",
    "LLM API errors",
)

# --- Agent-level metrics ---
agent_posts_total = _counter(
    "colloquip_agent_posts_total",
    "Posts generated per agent",
    labelnames=["agent_id", "stance", "phase"],
)
agent_tokens_total = _counter(
    "colloquip_agent_tokens_total",
    "Tokens used per agent",
    labelnames=["agent_id", "direction"],
)
agent_triggers_total = _counter(
    "colloquip_agent_triggers_total",
    "Trigger activations per agent",
    labelnames=["agent_id", "trigger_type"],
)
agent_novelty_score = _histogram(
    "colloquip_agent_novelty_score",
    "Novelty score distribution per agent",
    labelnames=["agent_id"],
    buckets=[0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
)
agent_citations_total = _counter(
    "colloquip_agent_citations_total",
    "Citations produced per agent",
    labelnames=["agent_id"],
)


@contextmanager
def track_duration(histogram):
    """Context manager to track operation duration."""
    start = time.monotonic()
    try:
        yield
    finally:
        histogram.observe(time.monotonic() - start)


def get_metrics_text() -> bytes:
    """Return Prometheus-formatted metrics text."""
    return generate_latest()
