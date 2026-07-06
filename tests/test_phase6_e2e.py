"""Phase 6 end-to-end integration test.

Drives a full deliberation with:
- A subreddit mission (program.md-style)
- Per-agent budgets — one agent pre-exhausted so it gets skipped
- An autoresearch-enabled agent
- Mission objectives measured via the /mission/progress endpoint
- An approval request surfaced via the API

The goal is to verify that all Phase 6 surfaces work together end-to-end with
the mock LLM stack, not to benchmark real behavior.
"""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from colloquip.agents.base import BaseDeliberationAgent
from colloquip.autoresearch import MockAutoresearchLoop
from colloquip.cost_tracker import CostTracker
from colloquip.energy import EnergyCalculator
from colloquip.engine import EmergentDeliberationEngine
from colloquip.llm.mock import MockBehavior, MockLLM
from colloquip.models import (
    AgentBudgetSkipped,
    AgentConfig,
    ConsensusMap,
    DeliberationSession,
    Phase,
    Post,
)
from colloquip.observer import ObserverAgent
from colloquip.subreddit_mission import parse_objectives


def _make_agent_config(agent_id: str, keywords=None, autoresearch: bool = False) -> AgentConfig:
    return AgentConfig(
        agent_id=agent_id,
        display_name=agent_id.upper(),
        persona_prompt=f"You are the {agent_id} expert.",
        phase_mandates={p: "" for p in Phase},
        domain_keywords=keywords or [agent_id, "hypothesis"],
        knowledge_scope=[agent_id],
        autoresearch_enabled=autoresearch,
    )


@pytest.mark.asyncio
async def test_phase6_end_to_end_engine_flow():
    """Exercise the engine with mission, budget skip, and autoresearch together."""
    from colloquip.approvals import ApprovalQueue
    from colloquip.models import ApprovalRequestType

    # --- Build agents: alpha (autoresearch on), beta (red-team), gamma (budget-locked)
    # All three agents share the "hypothesis" keyword so they all naturally
    # trigger in the main loop — we want gamma's budget breach to surface as
    # an event from _generate_posts_with_budget_gate, not just be silently
    # skipped in the seed phase.
    alpha = BaseDeliberationAgent(
        config=_make_agent_config("alpha", keywords=["hypothesis", "alpha"], autoresearch=True),
        llm=MockLLM(behavior=MockBehavior.MIXED, seed=1),
        autoresearch_loop=MockAutoresearchLoop(),
    )
    beta = BaseDeliberationAgent(
        config=_make_agent_config("beta", keywords=["hypothesis", "critique"]),
        llm=MockLLM(behavior=MockBehavior.ALWAYS_CRITICAL, seed=2),
    )
    gamma = BaseDeliberationAgent(
        config=_make_agent_config("gamma", keywords=["hypothesis", "gamma"]),
        llm=MockLLM(behavior=MockBehavior.MIXED, seed=3),
    )
    agents = {"alpha": alpha, "beta": beta, "gamma": gamma}

    # --- Mission
    mission_md = (
        "# Mission\n\n"
        "Validate GLP-1 for cognition.\n\n"
        "## Objective: Reach novelty target\n"
        "- metric: novelty_avg\n"
        "- target: 0.0\n"
    )
    objectives = parse_objectives(mission_md)
    assert len(objectives) == 1

    # --- Cost tracker with gamma pre-exhausted
    session_id = uuid4()
    cost_tracker = CostTracker(cost_per_input_token=1e-6, cost_per_output_token=1e-6)
    cost_tracker.start_tracking(session_id)
    cost_tracker.record(session_id, input_tokens=10_000_000, output_tokens=0, agent_id="gamma")

    approval_queue = ApprovalQueue()
    subreddit_uuid = uuid4()
    engine = EmergentDeliberationEngine(
        agents=agents,
        observer=ObserverAgent(energy_calculator=EnergyCalculator()),
        energy_calculator=EnergyCalculator(),
        llm=MockLLM(seed=42),
        max_turns=4,
        min_posts=3,
        cost_tracker=cost_tracker,
        session_id=session_id,
        subreddit_id=subreddit_uuid,
        subreddit_mission=mission_md,
        mission_objectives=objectives,
        agent_budgets={"gamma": 0.001},
        approval_queue=approval_queue,
    )

    session = DeliberationSession(id=session_id, hypothesis="GLP-1 hypothesis improves cognition")

    posts: list[Post] = []
    skips: list[AgentBudgetSkipped] = []
    consensus: ConsensusMap | None = None
    async for event in engine.run_deliberation(session, session.hypothesis):
        if isinstance(event, Post):
            posts.append(event)
        elif isinstance(event, AgentBudgetSkipped):
            skips.append(event)
        elif isinstance(event, ConsensusMap):
            consensus = event

    # --- Assertions
    assert len(posts) > 0, "expected at least one post from non-budget-locked agents"
    assert consensus is not None, "expected final synthesis"

    # gamma should never post; the budget gate keeps it out of every turn
    posting_agents = {p.agent_id for p in posts}
    assert "gamma" not in posting_agents
    assert "alpha" in posting_agents or "beta" in posting_agents

    # The main loop should yield at least one AgentBudgetSkipped event tagged
    # with gamma + agent_thread_budget — proves the breach surfaced, not just
    # got silently skipped at the seed phase boundary.
    gamma_skips = [s for s in skips if s.agent_id == "gamma"]
    assert len(gamma_skips) >= 1, (
        f"gamma should produce a skip event from the main loop; got {skips}"
    )
    assert all(s.reason == "agent_thread_budget" for s in gamma_skips)

    # Engine should have routed gamma's breach to the approval queue as a
    # BUDGET_OVERRIDE request, idempotently (one entry, not many).
    pending = approval_queue.pending_for_subreddit(str(subreddit_uuid))
    assert len(pending) == 1, f"expected 1 dedup'd budget override; got {pending}"
    assert pending[0].request_type == ApprovalRequestType.BUDGET_OVERRIDE
    assert pending[0].initiator == "agent:gamma"


class TestPhase6ApiE2E:
    @pytest.fixture
    def client(self):
        from colloquip.api import create_app

        return TestClient(create_app())

    def test_mission_progress_and_approval_flow(self, client):
        # Init + create a subreddit
        client.post("/api/platform/init")
        resp = client.post(
            "/api/subreddits",
            json={
                "name": "e2e_phase6",
                "display_name": "Phase 6 E2E",
                "description": "End-to-end Phase 6 smoke test",
                "thinking_type": "assessment",
                "required_expertise": ["molecular_biology"],
                "primary_domain": "drug_discovery",
            },
        )
        assert resp.status_code == 200

        # Set a mission
        resp = client.put(
            "/api/subreddits/e2e_phase6/mission",
            json={
                "mission_md": (
                    "## Objective: Novelty goal\n- metric: novelty_avg\n- target: 0.3\n"
                    "## Objective: Qualitative trust\nBuild expert trust.\n"
                )
            },
        )
        assert resp.status_code == 200, resp.text
        mission = resp.json()
        assert len(mission["objectives"]) == 2

        # Goal progress endpoint returns both
        progress = client.get("/api/subreddits/e2e_phase6/mission/progress").json()
        titles = {o["title"] for o in progress["objectives"]}
        assert {"Novelty goal", "Qualitative trust"}.issubset(titles)

        # Org chart renders for the recruited agents
        chart = client.get("/api/subreddits/e2e_phase6/org-chart").json()
        assert len(chart["nodes"]) >= 1

        # Budgets initially empty overrides
        budgets = client.get("/api/subreddits/e2e_phase6/budgets").json()
        assert budgets["members"]

        # Approval flow: enqueue → list pending → resolve → verify gone
        resp = client.post(
            "/api/subreddits/e2e_phase6/approvals",
            json={
                "request_type": "budget_override",
                "initiator": "agent:alpha",
                "reason": "Need more tokens",
                "estimated_cost_usd": 0.25,
            },
        )
        assert resp.status_code == 200
        req_id = resp.json()["id"]

        pending = client.get("/api/subreddits/e2e_phase6/approvals?status=pending").json()[
            "approvals"
        ]
        assert len(pending) == 1

        resolve = client.post(
            f"/api/approvals/{req_id}/resolve",
            json={"status": "approved", "decided_by": "user:admin"},
        )
        assert resolve.status_code == 200
        assert resolve.json()["status"] == "approved"

        pending_after = client.get("/api/subreddits/e2e_phase6/approvals?status=pending").json()[
            "approvals"
        ]
        assert pending_after == []
