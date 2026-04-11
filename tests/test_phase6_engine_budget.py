"""Phase 6 engine-level budget enforcement tests.

Drives the implementation of per-agent budget gating in
EmergentDeliberationEngine._generate_posts: agents that exceed their per-thread
budget should be skipped and an AgentBudgetSkipped event yielded. The thread
itself should not crash — the remaining agents continue deliberating.
"""

from uuid import uuid4

import pytest

from colloquip.agents.base import BaseDeliberationAgent
from colloquip.cost_tracker import CostTracker
from colloquip.energy import EnergyCalculator
from colloquip.engine import EmergentDeliberationEngine
from colloquip.llm.mock import MockLLM
from colloquip.models import (
    AgentBudgetSkipped,
    AgentConfig,
    ConversationMetrics,
    DeliberationSession,
    Phase,
    PhaseSignal,
    Post,
)
from colloquip.observer import ObserverAgent


def _make_config(agent_id: str, keywords=None) -> AgentConfig:
    return AgentConfig(
        agent_id=agent_id,
        display_name=agent_id.upper(),
        persona_prompt=f"You are the {agent_id} expert.",
        phase_mandates={p: "" for p in Phase},
        domain_keywords=keywords or [agent_id],
        knowledge_scope=[agent_id],
    )


class _HighCostLLM(MockLLM):
    """MockLLM that reports large token counts so budgets are quickly consumed."""

    async def generate(self, system_prompt, user_prompt, max_tokens=None):
        result = await super().generate(system_prompt, user_prompt, max_tokens)
        # Override the token counts so each call reports inflated usage.
        result.input_tokens = 1_000_000
        result.output_tokens = 1_000_000
        return result


@pytest.mark.asyncio
class TestEnginePerAgentBudgetGate:
    async def test_agent_exceeding_budget_is_skipped_and_event_yielded(self):
        alpha = BaseDeliberationAgent(config=_make_config("alpha"), llm=_HighCostLLM(seed=1))
        beta = BaseDeliberationAgent(config=_make_config("beta"), llm=MockLLM(seed=2))
        agents = {"alpha": alpha, "beta": beta}

        cost_tracker = CostTracker(cost_per_input_token=1e-6, cost_per_output_token=1e-6)
        session_id = uuid4()
        cost_tracker.start_tracking(session_id)

        # Pre-record alpha's budget as already exhausted for this thread
        cost_tracker.record(
            session_id,
            input_tokens=10_000_000,
            output_tokens=10_000_000,
            agent_id="alpha",
        )

        engine = EmergentDeliberationEngine(
            agents=agents,
            observer=ObserverAgent(energy_calculator=EnergyCalculator()),
            energy_calculator=EnergyCalculator(),
            llm=MockLLM(seed=0),
            max_turns=2,
            min_posts=2,
            cost_tracker=cost_tracker,
            session_id=session_id,
            agent_budgets={"alpha": 0.001},  # way below current cost of 20.0
        )

        session = DeliberationSession(id=session_id, hypothesis="Test hypothesis")
        phase_signal = PhaseSignal(
            current_phase=Phase.EXPLORE,
            confidence=1.0,
            metrics=ConversationMetrics(
                question_rate=0.0,
                disagreement_rate=0.0,
                topic_diversity=0.0,
                citation_density=0.0,
                novelty_avg=0.0,
                energy=1.0,
                posts_since_novel=0,
            ),
        )

        # Drive _generate_posts directly (skip the full loop)
        responding = {"alpha": ["seed_phase"], "beta": ["seed_phase"]}
        emitted = []
        async for event in engine._generate_posts_with_budget_gate(
            responding, session, phase_signal, posts=[]
        ):
            emitted.append(event)

        posts = [e for e in emitted if isinstance(e, Post)]
        skips = [e for e in emitted if isinstance(e, AgentBudgetSkipped)]

        # alpha should be skipped; beta should still post
        assert len(posts) == 1
        assert posts[0].agent_id == "beta"
        assert len(skips) == 1
        assert skips[0].agent_id == "alpha"
        assert skips[0].reason == "agent_thread_budget"

    async def test_thread_budget_skip_emitted_once_per_turn(self):
        """Regression: thread-budget breaches should emit one event per turn,
        not one per agent. The cap is shared across all agents, so N events
        would be noise."""
        alpha = BaseDeliberationAgent(config=_make_config("alpha"), llm=MockLLM(seed=1))
        beta = BaseDeliberationAgent(config=_make_config("beta"), llm=MockLLM(seed=2))
        gamma = BaseDeliberationAgent(config=_make_config("gamma"), llm=MockLLM(seed=3))
        agents = {"alpha": alpha, "beta": beta, "gamma": gamma}

        cost_tracker = CostTracker(cost_per_input_token=1e-6, cost_per_output_token=1e-6)
        session_id = uuid4()
        cost_tracker.start_tracking(session_id)
        # Pre-record so the thread total is over cap
        cost_tracker.record(session_id, 5_000_000, 5_000_000, agent_id="seed")

        engine = EmergentDeliberationEngine(
            agents=agents,
            observer=ObserverAgent(energy_calculator=EnergyCalculator()),
            energy_calculator=EnergyCalculator(),
            llm=MockLLM(seed=0),
            max_turns=2,
            min_posts=2,
            cost_tracker=cost_tracker,
            session_id=session_id,
            max_cost_per_thread_usd=0.001,
        )

        session = DeliberationSession(id=session_id, hypothesis="Test")
        signal = PhaseSignal(
            current_phase=Phase.EXPLORE,
            confidence=1.0,
            metrics=ConversationMetrics(
                question_rate=0.0,
                disagreement_rate=0.0,
                topic_diversity=0.0,
                citation_density=0.0,
                novelty_avg=0.0,
                energy=1.0,
                posts_since_novel=0,
            ),
        )
        responding = {"alpha": ["x"], "beta": ["x"], "gamma": ["x"]}
        emitted = []
        async for event in engine._generate_posts_with_budget_gate(
            responding, session, signal, posts=[], turn=1
        ):
            emitted.append(event)

        skips = [e for e in emitted if isinstance(e, AgentBudgetSkipped)]
        # Three agents tripped the same thread budget — only one event yielded
        assert len(skips) == 1, f"expected 1 dedup'd event, got {len(skips)}: {skips}"
        assert skips[0].reason == "thread_budget"

    async def test_agent_breach_enqueues_approval_request(self):
        from colloquip.approvals import ApprovalQueue
        from colloquip.models import ApprovalRequestType

        alpha = BaseDeliberationAgent(config=_make_config("alpha"), llm=_HighCostLLM(seed=1))
        agents = {"alpha": alpha}

        cost_tracker = CostTracker(cost_per_input_token=1e-6, cost_per_output_token=1e-6)
        session_id = uuid4()
        cost_tracker.record(session_id, 10_000_000, 0, agent_id="alpha")

        approval_queue = ApprovalQueue()
        subreddit_id = uuid4()
        engine = EmergentDeliberationEngine(
            agents=agents,
            observer=ObserverAgent(energy_calculator=EnergyCalculator()),
            energy_calculator=EnergyCalculator(),
            llm=MockLLM(seed=0),
            max_turns=2,
            min_posts=1,
            cost_tracker=cost_tracker,
            session_id=session_id,
            agent_budgets={"alpha": 0.001},
            approval_queue=approval_queue,
            subreddit_id=subreddit_id,
        )
        session = DeliberationSession(id=session_id, hypothesis="Test")
        signal = PhaseSignal(
            current_phase=Phase.EXPLORE,
            confidence=1.0,
            metrics=ConversationMetrics(
                question_rate=0.0,
                disagreement_rate=0.0,
                topic_diversity=0.0,
                citation_density=0.0,
                novelty_avg=0.0,
                energy=1.0,
                posts_since_novel=0,
            ),
        )
        responding = {"alpha": ["x"]}
        emitted = []
        async for event in engine._generate_posts_with_budget_gate(
            responding, session, signal, posts=[], turn=1
        ):
            emitted.append(event)

        pending = approval_queue.pending_for_subreddit(str(subreddit_id))
        assert len(pending) == 1
        req = pending[0]
        assert req.request_type == ApprovalRequestType.BUDGET_OVERRIDE
        assert req.initiator == "agent:alpha"
        assert req.payload["reason"] == "agent_thread_budget"

        # Idempotent: hitting it again on the same engine should NOT add another
        async for _ in engine._generate_posts_with_budget_gate(
            responding, session, signal, posts=[], turn=2
        ):
            pass
        pending_after = approval_queue.pending_for_subreddit(str(subreddit_id))
        assert len(pending_after) == 1, "approval enqueue should be deduped"

    async def test_monthly_budget_cap_enforced(self):
        """Regression: monthly budget should be enforced via the
        DB-loaded baseline + in-memory thread spend."""
        alpha = BaseDeliberationAgent(config=_make_config("alpha"), llm=MockLLM(seed=1))
        agents = {"alpha": alpha}

        cost_tracker = CostTracker(cost_per_input_token=1e-6, cost_per_output_token=1e-6)
        session_id = uuid4()
        engine = EmergentDeliberationEngine(
            agents=agents,
            observer=ObserverAgent(energy_calculator=EnergyCalculator()),
            energy_calculator=EnergyCalculator(),
            llm=MockLLM(seed=0),
            max_turns=2,
            min_posts=1,
            cost_tracker=cost_tracker,
            session_id=session_id,
            agent_monthly_budgets={"alpha": 1.0},
            agent_monthly_used={"alpha": 1.5},  # already over the cap
        )
        session = DeliberationSession(id=session_id, hypothesis="Test")
        signal = PhaseSignal(
            current_phase=Phase.EXPLORE,
            confidence=1.0,
            metrics=ConversationMetrics(
                question_rate=0.0,
                disagreement_rate=0.0,
                topic_diversity=0.0,
                citation_density=0.0,
                novelty_avg=0.0,
                energy=1.0,
                posts_since_novel=0,
            ),
        )
        responding = {"alpha": ["x"]}
        emitted = []
        async for event in engine._generate_posts_with_budget_gate(
            responding, session, signal, posts=[], turn=1
        ):
            emitted.append(event)
        skips = [e for e in emitted if isinstance(e, AgentBudgetSkipped)]
        assert len(skips) == 1
        assert skips[0].reason == "agent_monthly_budget"

    async def test_usage_callback_invoked_after_each_call(self):
        """Regression: _record_cost should fire usage_callback so DB
        accumulators get updated."""
        alpha = BaseDeliberationAgent(config=_make_config("alpha"), llm=MockLLM(seed=1))
        agents = {"alpha": alpha}
        recorded = []

        async def callback(agent_id, in_tok, out_tok, cost):
            recorded.append((agent_id, in_tok, out_tok, cost))

        cost_tracker = CostTracker(cost_per_input_token=1e-6, cost_per_output_token=1e-6)
        engine = EmergentDeliberationEngine(
            agents=agents,
            observer=ObserverAgent(energy_calculator=EnergyCalculator()),
            energy_calculator=EnergyCalculator(),
            llm=MockLLM(seed=0),
            max_turns=2,
            min_posts=1,
            cost_tracker=cost_tracker,
            session_id=uuid4(),
            usage_callback=callback,
        )
        session = DeliberationSession(hypothesis="Test")
        signal = PhaseSignal(
            current_phase=Phase.EXPLORE,
            confidence=1.0,
            metrics=ConversationMetrics(
                question_rate=0.0,
                disagreement_rate=0.0,
                topic_diversity=0.0,
                citation_density=0.0,
                novelty_avg=0.0,
                energy=1.0,
                posts_since_novel=0,
            ),
        )
        responding = {"alpha": ["x"]}
        async for _ in engine._generate_posts_with_budget_gate(
            responding, session, signal, posts=[], turn=1
        ):
            pass
        # Allow scheduled async tasks to complete
        import asyncio as _asyncio

        await _asyncio.sleep(0.05)
        assert len(recorded) >= 1, "usage_callback should fire at least once"
        assert recorded[0][0] == "alpha"

    async def test_agent_within_budget_is_not_skipped(self):
        alpha = BaseDeliberationAgent(config=_make_config("alpha"), llm=MockLLM(seed=1))
        agents = {"alpha": alpha}

        cost_tracker = CostTracker(cost_per_input_token=1e-6, cost_per_output_token=1e-6)
        session_id = uuid4()
        engine = EmergentDeliberationEngine(
            agents=agents,
            observer=ObserverAgent(energy_calculator=EnergyCalculator()),
            energy_calculator=EnergyCalculator(),
            llm=MockLLM(seed=0),
            max_turns=2,
            min_posts=1,
            cost_tracker=cost_tracker,
            session_id=session_id,
            agent_budgets={"alpha": 100.0},
        )
        session = DeliberationSession(id=session_id, hypothesis="Test")
        phase_signal = PhaseSignal(
            current_phase=Phase.EXPLORE,
            confidence=1.0,
            metrics=ConversationMetrics(
                question_rate=0.0,
                disagreement_rate=0.0,
                topic_diversity=0.0,
                citation_density=0.0,
                novelty_avg=0.0,
                energy=1.0,
                posts_since_novel=0,
            ),
        )
        responding = {"alpha": ["seed_phase"]}
        emitted = []
        async for event in engine._generate_posts_with_budget_gate(
            responding, session, phase_signal, posts=[]
        ):
            emitted.append(event)
        assert any(isinstance(e, Post) for e in emitted)
        assert not any(isinstance(e, AgentBudgetSkipped) for e in emitted)
