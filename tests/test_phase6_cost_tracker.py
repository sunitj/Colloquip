"""Phase 6 CostTracker tests: per-agent cost slicing and enforcement.

Written test-first to drive the extension of CostTracker with agent_id-keyed
records, per-agent cost/summary lookups, and per-agent budget checks.
Backwards compatibility with the existing thread-level API must be preserved.
"""

from uuid import uuid4

import pytest

from colloquip.cost_tracker import CostTracker


class TestPerAgentCostTracking:
    def test_backwards_compat_without_agent_id(self):
        tracker = CostTracker(cost_per_input_token=0.0001, cost_per_output_token=0.0002)
        thread = uuid4()
        tracker.record(thread, input_tokens=100, output_tokens=50)
        assert tracker.estimated_cost(thread) == pytest.approx(0.02)
        assert tracker.num_calls(thread) == 1

    def test_record_with_agent_id_aggregates_per_agent(self):
        tracker = CostTracker(cost_per_input_token=0.0001, cost_per_output_token=0.0002)
        thread = uuid4()
        tracker.record(thread, 100, 50, agent_id="alpha")
        tracker.record(thread, 200, 100, agent_id="alpha")
        tracker.record(thread, 50, 25, agent_id="beta")

        assert tracker.agent_cost(thread, "alpha") == pytest.approx(0.06)
        assert tracker.agent_cost(thread, "beta") == pytest.approx(0.01)
        # Thread total still includes everything
        assert tracker.estimated_cost(thread) == pytest.approx(0.07)

    def test_agent_summary_breakdown(self):
        tracker = CostTracker(cost_per_input_token=0.0001, cost_per_output_token=0.0002)
        thread = uuid4()
        tracker.record(thread, 100, 50, agent_id="alpha")
        tracker.record(thread, 200, 100, agent_id="alpha")

        summary = tracker.agent_summary(thread, "alpha")
        assert summary["agent_id"] == "alpha"
        assert summary["input_tokens"] == 300
        assert summary["output_tokens"] == 150
        assert summary["total_tokens"] == 450
        assert summary["num_llm_calls"] == 2
        assert summary["estimated_cost_usd"] == pytest.approx(0.06)

    def test_agent_summary_for_unknown_agent_returns_zeros(self):
        tracker = CostTracker()
        thread = uuid4()
        summary = tracker.agent_summary(thread, "ghost")
        assert summary["input_tokens"] == 0
        assert summary["output_tokens"] == 0
        assert summary["estimated_cost_usd"] == 0.0
        assert summary["num_llm_calls"] == 0

    def test_check_agent_budget_respected(self):
        tracker = CostTracker(cost_per_input_token=0.0001, cost_per_output_token=0.0002)
        thread = uuid4()
        tracker.record(thread, 100, 50, agent_id="alpha")  # 0.02

        assert tracker.check_agent_budget(thread, "alpha", max_usd=0.03) is True
        assert tracker.check_agent_budget(thread, "alpha", max_usd=0.01) is False

    def test_all_agents_for_thread(self):
        tracker = CostTracker()
        thread = uuid4()
        tracker.record(thread, 10, 5, agent_id="alpha")
        tracker.record(thread, 20, 10, agent_id="beta")
        tracker.record(thread, 30, 15, agent_id="alpha")
        agents = sorted(tracker.all_agents(thread))
        assert agents == ["alpha", "beta"]
