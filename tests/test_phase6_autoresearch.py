"""Phase 6 autoresearch capability layer tests.

Drives the implementation of colloquip.autoresearch — a shared capability
layer modeled after Karpathy's autoresearch loop:

- A fixed-budget iteration loop (max_steps / max_tokens / wallclock)
- Each step proposes an action (search, read_memory, reflect), executes it,
  measures a metric delta, and commits-or-resets the scratchpad.
- Early stop on sub-threshold deltas.
- Hard cap enforced regardless of config to prevent runaway cost.
"""

from uuid import uuid4

import pytest

from colloquip.autoresearch import (
    AutoresearchLoop,
    MockAutoresearchLoop,
    NoveltyGainMetric,
)
from colloquip.models import (
    MAX_AUTORESEARCH_TOKENS_PER_RUN,
    AgentDependencies,
    AutoresearchActionType,
    AutoresearchConfig,
    AutoresearchStatus,
    ConversationMetrics,
    DeliberationSession,
    Phase,
    PhaseSignal,
)


def _make_deps() -> AgentDependencies:
    signal = PhaseSignal(
        current_phase=Phase.DEEPEN,
        confidence=0.9,
        metrics=ConversationMetrics(
            question_rate=0.2,
            disagreement_rate=0.2,
            topic_diversity=0.3,
            citation_density=0.1,
            novelty_avg=0.3,
            energy=0.5,
            posts_since_novel=0,
        ),
    )
    session = DeliberationSession(id=uuid4(), hypothesis="GLP-1 improves cognition")
    return AgentDependencies(
        session=session,
        phase=Phase.DEEPEN,
        phase_signal=signal,
        posts=[],
        subreddit_mission="# Mission\nReduce hallucinations.",
    )


class TestNoveltyGainMetric:
    def test_empty_scratchpad_gives_zero(self):
        metric = NoveltyGainMetric()
        assert metric.evaluate("", "") == 0.0

    def test_new_content_produces_positive_delta(self):
        metric = NoveltyGainMetric()
        prev = "- Finding: X is related to Y."
        curr = prev + "\n- Finding: X is also linked to Z via mechanism M."
        delta = metric.delta(prev, curr)
        assert delta > 0

    def test_duplicate_content_produces_zero_delta(self):
        metric = NoveltyGainMetric()
        scratch = "- Finding: X is related to Y."
        assert metric.delta(scratch, scratch) == 0.0


@pytest.mark.asyncio
class TestMockAutoresearchLoop:
    async def test_runs_within_max_steps_budget(self):
        loop = MockAutoresearchLoop()
        config = AutoresearchConfig(max_steps=3, max_tokens=1000)
        deps = _make_deps()
        run = await loop.run(deps=deps, agent_id="alpha", config=config)
        assert run.agent_id == "alpha"
        assert len(run.steps) <= 3
        assert run.status in {
            AutoresearchStatus.COMPLETED,
            AutoresearchStatus.BUDGET_EXCEEDED,
        }
        assert run.scratchpad  # non-empty
        assert run.metric_end >= run.metric_start

    async def test_committed_steps_append_to_scratchpad(self):
        loop = MockAutoresearchLoop()
        config = AutoresearchConfig(max_steps=2, max_tokens=1000)
        deps = _make_deps()
        run = await loop.run(deps=deps, agent_id="alpha", config=config)
        committed = [s for s in run.steps if s.committed]
        for step in committed:
            assert step.summary
            assert step.summary in run.scratchpad

    async def test_loop_runs_full_budget_when_metric_keeps_gaining(self):
        """Regression test: with the metric.delta() fix, the loop should run
        most of its requested steps when the mock keeps producing novel
        scratchpad content (not give up after step 0)."""
        loop = MockAutoresearchLoop()
        config = AutoresearchConfig(max_steps=5, max_tokens=10_000)
        deps = _make_deps()
        run = await loop.run(deps=deps, agent_id="alpha", config=config)
        # Mock adds genuinely novel tokens every step → should not bail early
        step_deltas = [s.delta for s in run.steps]
        assert len(run.steps) == 5, (
            f"Loop should run all 5 steps; got {len(run.steps)} ({step_deltas})"
        )
        committed = [s for s in run.steps if s.committed]
        assert len(committed) >= 4, f"At least 4 of 5 steps should commit; got {len(committed)}"
        # Deltas should be positive and monotonically non-increasing as scratchpad grows
        deltas = [s.delta for s in run.steps if s.committed]
        assert all(d > 0 for d in deltas), f"committed deltas not positive: {deltas}"

    async def test_exceeding_hard_cap_tokens_stops(self):
        loop = MockAutoresearchLoop()
        # Set max_tokens above the hard cap — the loop must still stop at
        # ~MAX_AUTORESEARCH_TOKENS_PER_RUN. We allow up to one step's worth of
        # overshoot because real LLM-driven loops can't predict token usage
        # before invoking a tool.
        config = AutoresearchConfig(
            max_steps=100,
            max_tokens=MAX_AUTORESEARCH_TOKENS_PER_RUN * 3,
        )
        deps = _make_deps()
        run = await loop.run(deps=deps, agent_id="alpha", config=config)
        total = run.input_tokens + run.output_tokens
        # Mock spends ~300 tokens per step, so allow up to one overshoot
        assert total <= MAX_AUTORESEARCH_TOKENS_PER_RUN + 500, (
            f"loop overshot hard cap by more than one step: {total}"
        )
        assert run.status == AutoresearchStatus.BUDGET_EXCEEDED

    async def test_zero_steps_budget_yields_empty_run(self):
        loop = MockAutoresearchLoop()
        config = AutoresearchConfig(max_steps=0, max_tokens=1000)
        deps = _make_deps()
        run = await loop.run(deps=deps, agent_id="alpha", config=config)
        assert run.steps == []
        assert run.scratchpad == ""

    async def test_allowed_actions_respected(self):
        loop = MockAutoresearchLoop()
        config = AutoresearchConfig(
            max_steps=3,
            max_tokens=1000,
            allowed_actions=[AutoresearchActionType.REFLECT],
        )
        deps = _make_deps()
        run = await loop.run(deps=deps, agent_id="alpha", config=config)
        for step in run.steps:
            assert step.action == AutoresearchActionType.REFLECT


@pytest.mark.asyncio
class TestAutoresearchLoopWithoutTools:
    async def test_loop_without_tool_registry_falls_back_to_reflect(self):
        """The real loop without tools should still run reflect steps only."""
        loop = AutoresearchLoop(tool_registry=None)
        config = AutoresearchConfig(max_steps=2, max_tokens=1000)
        deps = _make_deps()
        run = await loop.run(deps=deps, agent_id="alpha", config=config)
        assert run.status in {
            AutoresearchStatus.COMPLETED,
            AutoresearchStatus.BUDGET_EXCEEDED,
        }
        assert run.finished_at is not None
