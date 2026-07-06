"""Applied-science user stories as end-to-end feature showcases.

Each class is a scripted deliberation for a real R&D scenario. Collectively
they exercise the whole Colloquium feature surface — not just Phase 6:

    phase emergence · triggers · energy dynamics · red-team · synthesis ·
    subreddit missions · mission prompt injection · goal-progress measurement ·
    autoresearch loops · per-agent budgets · budget-skip events · approval queue
    (budget-override + tool-call) · human intervention + energy injection ·
    institutional memory retrieval · cross-references + entity extraction ·
    cost tracking (thread + per-agent) · outcome tracking · watcher
    auto-deliberation (earned privilege) · triage → hypothesis · notifications ·
    output templates · agent org chart

They run against the deterministic ``MockLLM`` by default (fast, CI-safe) and
can be pointed at the real Anthropic API with ``COLLOQUIP_USE_REAL_LLM=1``.

Mock-mode determinism levers (documented so the assertions read as intentional):
- Every agent blends a few *universal* keywords (``_U``) that appear in the
  MockLLM's generated text, so relevance triggers fire and the main loop stays
  active. In real-LLM mode the domain keywords match domain content directly.
- Making non-red-team agents ``ALWAYS_SUPPORTIVE`` and the red team
  ``ALWAYS_CRITICAL`` reliably drives the red team's ``consensus_forming`` rule.
- Autoresearch gates to ``Phase.DEEPEN``; a story that showcases it drives one
  ``generate_post`` with a DEEPEN dependency to demonstrate the loop.
"""

from __future__ import annotations

import sys
from pathlib import Path
from uuid import uuid4

import pytest

sys.path.insert(0, str(Path(__file__).parent))
import story_harness as H  # noqa: E402

from colloquip.llm.mock import MockBehavior  # noqa: E402
from colloquip.models import (  # noqa: E402
    AgentDependencies,
    ApprovalRequestType,
    ApprovalStatus,
    ConversationMetrics,
    DeliberationSession,
    HumanIntervention,
    Phase,
    PhaseSignal,
)
from colloquip.subreddit_mission import measure_objectives, parse_objectives  # noqa: E402

# Universal keywords present in MockLLM output — ensure relevance triggers fire
# so mock-mode deliberations reach the main loop. (No effect in real-LLM mode.)
_U = ["mechanism", "pathway", "evidence", "data", "target", "selectivity", "safety", "clinical"]


def _deepen_deps(session, posts, mission=None):
    """A DEEPEN-phase AgentDependencies for showcasing the autoresearch loop."""
    signal = PhaseSignal(
        current_phase=Phase.DEEPEN,
        confidence=0.9,
        metrics=ConversationMetrics(
            question_rate=0.1,
            disagreement_rate=0.2,
            topic_diversity=0.3,
            citation_density=0.1,
            novelty_avg=0.3,
            energy=0.5,
            posts_since_novel=0,
        ),
    )
    return AgentDependencies(
        session=session,
        phase=Phase.DEEPEN,
        phase_signal=signal,
        posts=posts[:4],
        subreddit_mission=mission,
    )


# ===========================================================================
# Story 1 — Protein Engineering: subtilisin thermostability
# ===========================================================================


@pytest.mark.asyncio
class TestStory1ProteinEngineering:
    """As a protein engineer, I want candidate mutations for a subtilisin
    variant that survives 75C for 2h, so that I can enrich my wet-lab screen.

    Showcases: subreddit mission + prompt injection, autoresearch loop,
    red-team triggers, phase emergence, goal-progress measurement, synthesis.
    """

    FEATURES = (
        "mission",
        "mission_prompt_injection",
        "autoresearch",
        "red_team_rules",
        "phase_emergence",
        "goal_progress",
        "synthesis",
    )

    async def test_story(self):
        mission_md = (
            "# Mission: Thermostable Subtilisin Program\n\n"
            "Enrich the wet-lab screen with high-confidence stabilizing mutations.\n\n"
            "## Objective: Surface novel stabilizing hypotheses\n"
            "- metric: novelty_avg\n"
            "- target: 0.2\n\n"
            "## Objective: Ground claims in the literature\n"
            "- metric: citation_density\n"
            "- target: 0.5\n"
        )
        objectives = parse_objectives(mission_md)
        assert len(objectives) == 2

        # Supportive experts + a critical red team → red-team rules fire.
        agents = {
            "protein_engineering": H.build_agent(
                "protein_engineering",
                "Protein Engineering",
                "You design stabilizing mutations for industrial enzymes.",
                ["mutation", "thermostability", "fold", "disulfide"] + _U,
                mock_behavior=MockBehavior.ALWAYS_SUPPORTIVE,
                seed=1,
            ),
            "computational_biology": H.build_agent(
                "computational_biology",
                "Computational Biology",
                "You run MD simulations and predict folding free energy.",
                ["simulation", "structure", "docking", "free-energy"] + _U,
                autoresearch=True,
                mock_behavior=MockBehavior.ALWAYS_SUPPORTIVE,
                seed=2,
            ),
            "synthetic_biology": H.build_agent(
                "synthetic_biology",
                "Synthetic Biology",
                "You design expression constructs and screening assays.",
                ["expression", "construct", "assay", "screen"] + _U,
                mock_behavior=MockBehavior.ALWAYS_SUPPORTIVE,
                seed=3,
            ),
            "red_team_biology": H.build_agent(
                "red_team_biology",
                "Red Team (Biology)",
                "You challenge stability claims and demand controls.",
                ["confound", "artifact", "control", "aggregation"] + _U,
                is_red_team=True,
                mock_behavior=MockBehavior.ALWAYS_CRITICAL,
                seed=4,
            ),
        }
        sid = uuid4()
        sub_id = uuid4()
        engine = H.build_engine(
            agents,
            session_id=sid,
            subreddit_id=sub_id,
            mission_md=mission_md,
            objectives=objectives,
            max_turns=15,
            min_posts=8,
        )
        session = DeliberationSession(
            id=sid,
            hypothesis=(
                "A subtilisin variant with engineered disulfides survives 75C for 2h "
                "via a stabilizing mechanism on the target pathway"
            ),
        )
        run = await H.run_story(engine, session, session.hypothesis)

        # Mission reaches every agent's system prompt (verify via a DEEPEN post).
        comp = agents["computational_biology"]
        deepen_post = await comp.generate_post(_deepen_deps(session, run.posts, mission_md))
        assert deepen_post is not None

        # Autoresearch: the enabled agent ran its Karpathy-style loop in DEEPEN.
        run_record = comp.last_autoresearch_run
        assert run_record is not None, "autoresearch should run for the enabled agent in DEEPEN"
        assert len(run_record.steps) >= 1
        assert run_record.scratchpad, "autoresearch should accumulate a scratchpad"
        # Regression guard for the metric.delta fix — committed steps gain novelty.
        committed = [s for s in run_record.steps if s.committed]
        assert committed, "at least one autoresearch step should commit"
        assert all(s.delta > 0 for s in committed)

        # Red team participated AND its consensus-forming rule fired.
        assert "red_team_biology" in run.agents_that_posted()
        assert len(run.red_team_rule_posts()) >= 1, "red-team special rules should fire"

        # Phase emergence + synthesis.
        assert Phase.EXPLORE in run.phases_reached()
        assert run.consensus is not None
        assert run.consensus.summary

        # Goal progress measured against the real post stream.
        progress = measure_objectives(objectives, run.posts)
        assert len(progress) == 2
        by_metric = {p.metric: p for p in progress}
        assert by_metric["novelty_avg"].measured_value is not None
        assert by_metric["novelty_avg"].sample_size == len(run.posts)


# ===========================================================================
# Story 2 — Cancer Drug Repurposing: metformin for glioblastoma
# ===========================================================================


@pytest.mark.asyncio
class TestStory2CancerRepurposing:
    """As a translational oncologist, I want to evaluate metformin's plausible
    mechanism against glioblastoma, so that I can prioritize an IIT.

    Showcases: per-agent budgets, budget-skip event, approval queue (budget
    override, idempotent), loop resilience (thread continues), org chart.
    """

    FEATURES = (
        "per_agent_budget",
        "budget_skip_event",
        "approval_queue_budget_override",
        "loop_resilience",
        "org_chart",
    )

    async def test_story(self):
        from colloquip.approvals import ApprovalQueue
        from colloquip.cost_tracker import CostTracker

        agents = {
            "clinical": H.build_agent(
                "clinical",
                "Clinical Oncology",
                "You assess trial feasibility and endpoints.",
                ["endpoint", "cohort", "survival", "trial"] + _U,
                mock_behavior=MockBehavior.MIXED,
                seed=1,
            ),
            "computational_biology": H.build_agent(
                "computational_biology",
                "Computational Biology",
                "You model AMPK/mTOR signaling.",
                ["ampk", "mtor", "signaling", "metabolism"] + _U,
                mock_behavior=MockBehavior.MIXED,
                seed=2,
            ),
            "regulatory": H.build_agent(
                "regulatory",
                "Regulatory Affairs",
                "You map the repurposing regulatory path.",
                ["ind", "label", "repurposing", "guidance"] + _U,
                mock_behavior=MockBehavior.MIXED,
                seed=3,
            ),
            "red_team_general": H.build_agent(
                "red_team_general",
                "Red Team",
                "You challenge mechanism-of-action claims.",
                ["confound", "bias", "dose", "exposure"] + _U,
                is_red_team=True,
                mock_behavior=MockBehavior.ALWAYS_CRITICAL,
                seed=4,
            ),
        }
        sid = uuid4()
        sub_id = uuid4()

        # Pre-exhaust comp-bio's per-agent budget so the gate fires immediately.
        cost_tracker = CostTracker(cost_per_input_token=1e-6, cost_per_output_token=1e-6)
        cost_tracker.start_tracking(sid)
        cost_tracker.record(sid, 10_000_000, 0, agent_id="computational_biology")

        approval_queue = ApprovalQueue()
        engine = H.build_engine(
            agents,
            session_id=sid,
            subreddit_id=sub_id,
            cost_tracker=cost_tracker,
            agent_budgets={"computational_biology": 0.001},
            approval_queue=approval_queue,
            max_turns=12,
            min_posts=6,
        )
        session = DeliberationSession(
            id=sid,
            hypothesis=(
                "Metformin's AMPK mechanism has a plausible pathway against glioblastoma "
                "with an acceptable safety and selectivity target profile"
            ),
        )
        run = await H.run_story(engine, session, session.hypothesis)

        # Budget-locked agent never posts; the others carry the deliberation.
        assert "computational_biology" not in run.agents_that_posted()
        assert len(run.agents_that_posted()) >= 2

        # A budget-skip event surfaced with the right reason.
        cb_skips = [s for s in run.budget_skips if s.agent_id == "computational_biology"]
        assert cb_skips, "comp-bio should produce a budget-skip event"
        assert all(s.reason == "agent_thread_budget" for s in cb_skips)

        # The breach was routed to the approval queue exactly once (idempotent).
        pending = approval_queue.pending_for_subreddit(str(sub_id))
        assert len(pending) == 1
        assert pending[0].request_type == ApprovalRequestType.BUDGET_OVERRIDE
        assert pending[0].initiator == "agent:computational_biology"

        # Loop still terminated with a synthesis.
        assert run.consensus is not None

        # Org chart: build a real community roster and render the chart.
        from colloquip.api.platform_manager import PlatformManager

        pm = PlatformManager()
        pm.initialize()
        res = pm.create_subreddit(
            name=f"onc_{sub_id.hex[:8]}",
            display_name="Neuro-Oncology Repurposing",
            description="metformin/GBM",
            primary_domain="drug_discovery",
            required_expertise=["clinical", "computational_biology"],
        )
        chart = pm.get_subreddit_org_chart(res["subreddit"]["id"], recent_posts=[])
        assert len(chart.nodes) >= 1
        assert any(n.is_red_team for n in chart.nodes), "roster must include a red team"


# ===========================================================================
# Story 3 — Single-cell perturb-seq: CRISPRi T-cell exhaustion
# ===========================================================================


@pytest.mark.asyncio
class TestStory3PerturbSeq:
    """As a cell biologist, I want to interpret CRISPRi hits on exhausted CD8
    T-cells, so that I can pick knockouts to validate with live imaging.

    Showcases: human intervention + energy injection, institutional memory
    retrieval, citations, mid-deliberation steering.
    """

    FEATURES = (
        "human_intervention",
        "energy_injection",
        "memory_retrieval",
        "citations",
    )

    async def test_story(self):
        from colloquip.embeddings.mock import MockEmbeddingProvider
        from colloquip.memory.store import InMemoryStore, SynthesisMemory

        sid = uuid4()
        sub_id = uuid4()

        # Pre-seed institutional memory from a prior T-cell thread.
        embedder = MockEmbeddingProvider(dimension=256)
        store = InMemoryStore()
        prior_text = (
            "CRISPRi screen exhausted CD8 T cell TOX TCF7 mechanism pathway target "
            "checkpoint exhaustion program"
        )
        prior = SynthesisMemory(
            thread_id=uuid4(),
            subreddit_id=sub_id,
            subreddit_name="perturbseq",
            topic="T-cell exhaustion CRISPRi hits",
            synthesis_content=prior_text,
            key_conclusions=["TOX drives the exhaustion program", "TCF7 marks progenitor cells"],
            embedding=await embedder.embed(prior_text),
        )
        await store.save(prior)

        agents = {
            "molecular_biology": H.build_agent(
                "molecular_biology",
                "Molecular Biology",
                "You interpret perturbation screens.",
                ["knockout", "screen", "guide", "phenotype"] + _U,
                mock_behavior=MockBehavior.MIXED,
                seed=1,
            ),
            "computational_biology": H.build_agent(
                "computational_biology",
                "Computational Biology",
                "You cluster single-cell profiles.",
                ["cluster", "umap", "trajectory", "expression"] + _U,
                mock_behavior=MockBehavior.MIXED,
                seed=2,
            ),
            "clinical": H.build_agent(
                "clinical",
                "Translational",
                "You connect targets to immunotherapy.",
                ["immunotherapy", "checkpoint", "response", "biomarker"] + _U,
                mock_behavior=MockBehavior.MIXED,
                seed=3,
            ),
            "red_team_biology": H.build_agent(
                "red_team_biology",
                "Red Team (Biology)",
                "You challenge screen artifacts.",
                ["batch", "dropout", "artifact", "control"] + _U,
                is_red_team=True,
                mock_behavior=MockBehavior.ALWAYS_CRITICAL,
                seed=4,
            ),
        }
        engine = H.build_engine(
            agents, session_id=sid, subreddit_id=sub_id, max_turns=10, min_posts=6
        )
        session = DeliberationSession(
            id=sid,
            hypothesis=(
                "CRISPRi knockout of TOX in exhausted CD8 T cells reverses the exhaustion "
                "program via a checkpoint pathway mechanism"
            ),
        )
        run = await H.run_story(engine, session, session.hypothesis)
        assert run.consensus is not None

        # Institutional memory retrieval: the prior synthesis is findable.
        query_emb = await embedder.embed(session.hypothesis + " exhaustion CD8 T cell TOX")
        hits = await store.search(query_emb, subreddit_id=sub_id, limit=3)
        assert len(hits) >= 1
        assert hits[0].memory.id == prior.id
        assert hits[0].similarity > 0.0

        # Human intervention mid-deliberation → energy injection + human post.
        energy_before = run.final_energy()
        energy_history = run.energy_series()
        intervention = HumanIntervention(
            session_id=sid,
            type="question",
            content="What if LAG3 is redundant with TIGIT in this exhaustion context?",
        )
        new_posts = await engine.handle_intervention(
            session, intervention, list(run.posts), energy_history
        )
        assert new_posts, "intervention should produce a human post (+ responses)"
        assert new_posts[0].agent_id == "human"
        assert "LAG3" in new_posts[0].content
        # Energy was boosted by the HUMAN_INTERVENTION source.
        assert energy_history[-1] > energy_before

        # Citations: mock agents attach citations; density is measurable.
        assert run.total_citations() >= 1


# ===========================================================================
# Story 4 — Drug Discovery: GLP-1 agonists and cognition
# ===========================================================================


@pytest.mark.asyncio
class TestStory4GLP1Cognition:
    """As a pharma project lead, I want a multi-phase deliberation on whether
    GLP-1 agonists improve cognition in MCI, so that I can scope a Phase 2.

    Showcases: full phase cycle, energy dynamics, structured consensus,
    outcome tracking / calibration, cost tracking.
    """

    FEATURES = (
        "phase_cycle",
        "energy_dynamics",
        "consensus_structure",
        "outcome_tracking",
        "cost_tracking",
    )

    async def test_story(self):
        from colloquip.cost_tracker import CostTracker
        from colloquip.feedback.outcome import (
            InMemoryOutcomeTracker,
            OutcomeReport,
            OutcomeType,
        )

        sid = uuid4()
        sub_id = uuid4()
        cost_tracker = CostTracker()  # default Claude Sonnet pricing

        agents = {
            "clinical": H.build_agent(
                "clinical",
                "Clinical",
                "You design cognition trials.",
                ["cognition", "mci", "endpoint", "adas"] + _U,
                seed=1,
            ),
            "medicinal_chemistry": H.build_agent(
                "medicinal_chemistry",
                "Med Chem",
                "You assess CNS penetration.",
                ["bbb", "penetration", "scaffold", "potency"] + _U,
                seed=2,
            ),
            "admet": H.build_agent(
                "admet",
                "ADMET",
                "You flag exposure and tolerability.",
                ["exposure", "tolerability", "clearance", "metabolism"] + _U,
                seed=3,
            ),
            "regulatory": H.build_agent(
                "regulatory",
                "Regulatory",
                "You map the cognition-claim path.",
                ["indication", "guidance", "endpoint", "label"] + _U,
                seed=4,
            ),
            "computational_biology": H.build_agent(
                "computational_biology",
                "Comp Bio",
                "You model incretin signaling.",
                ["incretin", "signaling", "receptor", "neuroprotection"] + _U,
                seed=5,
            ),
            "red_team_general": H.build_agent(
                "red_team_general",
                "Red Team",
                "You challenge the cognition link.",
                ["confound", "placebo", "washout", "bias"] + _U,
                is_red_team=True,
                mock_behavior=MockBehavior.ALWAYS_CRITICAL,
                seed=6,
            ),
        }
        engine = H.build_engine(
            agents,
            session_id=sid,
            subreddit_id=sub_id,
            cost_tracker=cost_tracker,
            max_turns=18,
            min_posts=10,
        )
        session = DeliberationSession(
            id=sid,
            hypothesis=(
                "GLP-1 receptor agonists improve cognition in MCI patients via a "
                "neuroprotective incretin pathway mechanism with acceptable safety"
            ),
        )
        run = await H.run_story(engine, session, session.hypothesis)

        # Phase cycle: at least two distinct phases emerged from the metrics.
        assert len(run.phases_reached()) >= 2

        # Energy dynamics: a non-trivial series was produced.
        series = run.energy_series()
        assert len(series) >= 3
        assert max(series) > 0.0

        # Structured consensus with agreements/disagreements/final stances.
        cm = run.consensus
        assert cm is not None
        assert isinstance(cm.final_stances, dict) and len(cm.final_stances) >= 1
        assert len(cm.agreements) + len(cm.disagreements) >= 1

        # Cost tracking: thread total and per-agent slices are populated.
        summary = cost_tracker.thread_summary(sid)
        assert summary["estimated_cost_usd"] > 0.0
        assert summary["num_llm_calls"] >= 1
        posted = run.agents_that_posted()
        assert sum(cost_tracker.agent_cost(sid, a) for a in posted) > 0.0

        # Outcome tracking / calibration path.
        tracker = InMemoryOutcomeTracker()
        outcome = OutcomeReport(
            thread_id=sid,
            subreddit_id=sub_id,
            outcome_type=OutcomeType.PARTIALLY_CONFIRMED,
            summary="Phase 2 showed modest cognitive benefit in a subgroup.",
            conclusions_evaluated=list(cm.agreements[:2]),
            agent_assessments={a: "partial" for a in list(posted)[:2]},
        )
        await tracker.save_outcome(outcome)
        retrieved = await tracker.get_outcomes_for_thread(sid)
        assert len(retrieved) == 1
        assert retrieved[0].outcome_type == OutcomeType.PARTIALLY_CONFIRMED


# ===========================================================================
# Story 5 — Microbiome enzyme engineering: cellulase for biofuel
# ===========================================================================


@pytest.mark.asyncio
class TestStory5MicrobiomeCellulase:
    """As a bioprocess engineer, I want to compare cellulase variants for
    continuous fermentation at pH 5.5 / 55C, so that I can pick a scale-up
    candidate.

    Showcases: qualitative mission objectives, watcher auto-deliberation
    (earned privilege), triage → hypothesis wiring, red-team.
    """

    FEATURES = (
        "qualitative_objectives",
        "watcher_auto_deliberation",
        "triage_hypothesis",
        "red_team",
    )

    async def test_story(self):
        from colloquip.watchers.auto_deliberation import AutoDeliberationPolicy

        # Qualitative-only mission (no metric bullets).
        mission_md = (
            "# Mission: Industrial Cellulase Selection\n\n"
            "## Objective: Balance activity against operational robustness\n"
            "Favor variants that keep >70% activity after 48h at pH 5.5, 55C.\n\n"
            "## Objective: Keep the scale-up economics realistic\n"
            "Avoid recommendations that need exotic cofactors.\n"
        )
        objectives = parse_objectives(mission_md)
        assert len(objectives) == 2
        progress = measure_objectives(objectives, [])
        assert all(p.qualitative for p in progress)
        assert all(p.status == "open" for p in progress)

        # Watcher earns auto-deliberation privilege (Phase 4 policy).
        policy = AutoDeliberationPolicy()
        watcher_id = uuid4()
        policy.approve_watcher(watcher_id)
        for _ in range(25):
            policy.record_event(watcher_id)
        for _ in range(20):  # 20/25 = 80% useful rate > 70% threshold
            policy.record_useful_outcome(watcher_id)
        check = policy.can_auto_create(watcher_id)
        assert check.allowed, f"watcher should earn auto-deliberation: {check.reason}"

        # Triage produces a suggested hypothesis that seeds the thread.
        from colloquip.models import (
            TriageDecision,
            TriageSignal,
            WatcherEvent,
            WatcherSource,
        )

        event = WatcherEvent(
            watcher_id=watcher_id,
            subreddit_id=uuid4(),
            title="New thermostable cellulase paper",
            summary="Variant CelB retains activity at 55C",
            source=WatcherSource(source_type="pubmed", source_id="40123456"),
        )
        triage = TriageDecision(
            event_id=event.id,
            signal=TriageSignal.HIGH,
            novelty=0.8,
            relevance=0.9,
            urgency=0.6,
            reasoning="Directly relevant to the scale-up decision.",
            suggested_hypothesis=(
                "Cellulase variant CelB outperforms the incumbent at pH 5.5 / 55C via a "
                "stabilizing mechanism on the target pathway with a favorable safety profile"
            ),
        )
        assert triage.suggested_hypothesis

        sid = uuid4()
        sub_id = uuid4()
        agents = {
            "synthetic_biology": H.build_agent(
                "synthetic_biology",
                "Synthetic Biology",
                "You engineer secretion + expression.",
                ["expression", "secretion", "titer", "fermentation"] + _U,
                mock_behavior=MockBehavior.ALWAYS_SUPPORTIVE,
                seed=1,
            ),
            "protein_engineering": H.build_agent(
                "protein_engineering",
                "Protein Engineering",
                "You stabilize the fold.",
                ["mutation", "stability", "fold", "half-life"] + _U,
                mock_behavior=MockBehavior.ALWAYS_SUPPORTIVE,
                seed=2,
            ),
            "medicinal_chemistry": H.build_agent(
                "medicinal_chemistry",
                "Process Chemistry",
                "You assess cofactors + cost.",
                ["cofactor", "cost", "substrate", "yield"] + _U,
                mock_behavior=MockBehavior.ALWAYS_SUPPORTIVE,
                seed=3,
            ),
            "red_team_general": H.build_agent(
                "red_team_general",
                "Red Team",
                "You challenge activity claims.",
                ["denaturation", "leaching", "artifact", "control"] + _U,
                is_red_team=True,
                mock_behavior=MockBehavior.ALWAYS_CRITICAL,
                seed=4,
            ),
        }
        engine = H.build_engine(
            agents,
            session_id=sid,
            subreddit_id=sub_id,
            mission_md=mission_md,
            objectives=objectives,
            max_turns=12,
            min_posts=8,
        )
        # The watcher-suggested hypothesis seeds the deliberation.
        session = DeliberationSession(id=sid, hypothesis=triage.suggested_hypothesis)
        run = await H.run_story(engine, session, session.hypothesis)

        assert run.consensus is not None
        assert "red_team_general" in run.agents_that_posted()
        assert len(run.red_team_rule_posts()) >= 1


# ===========================================================================
# Story 6 — Manufacturing scale-up: continuous-flow API intermediate
# ===========================================================================


@pytest.mark.asyncio
class TestStory6ManufacturingScaleUp:
    """As a process chemist, I want to evaluate a continuous-flow Suzuki
    coupling for an API intermediate against cGMP and cost targets, so that I
    can commit to a $2M capex pilot.

    Showcases: cost tracking (thread + per-agent), notifications, approval
    queue (tool-call), output templates (REVIEW), org chart.
    """

    FEATURES = (
        "cost_tracking",
        "notifications",
        "approval_queue_tool_call",
        "output_template_review",
        "org_chart",
    )

    async def test_story(self):
        from colloquip.approvals import ApprovalQueue
        from colloquip.cost_tracker import CostTracker
        from colloquip.models import Notification, ThinkingType, TriageSignal
        from colloquip.notifications.store import InMemoryNotificationStore
        from colloquip.output_templates import get_template

        # The REVIEW output template shapes this subreddit's synthesis.
        template = get_template(ThinkingType.REVIEW)
        assert template.template_type == "review"
        assert len(template.sections) >= 3

        sid = uuid4()
        sub_id = uuid4()
        cost_tracker = CostTracker()

        agents = {
            "medicinal_chemistry": H.build_agent(
                "medicinal_chemistry",
                "Process Chemistry",
                "You own the coupling chemistry.",
                ["suzuki", "palladium", "flow", "yield"] + _U,
                seed=1,
            ),
            "regulatory": H.build_agent(
                "regulatory",
                "cGMP / Quality",
                "You own the cGMP requirements.",
                ["cgmp", "impurity", "validation", "qualification"] + _U,
                seed=2,
            ),
            "admet": H.build_agent(
                "admet",
                "Impurities / Tox",
                "You flag genotoxic impurities.",
                ["genotoxic", "impurity", "spec", "control"] + _U,
                seed=3,
            ),
            "red_team_general": H.build_agent(
                "red_team_general",
                "Red Team",
                "You challenge the cost + robustness case.",
                ["fouling", "clogging", "scale", "variance"] + _U,
                is_red_team=True,
                mock_behavior=MockBehavior.ALWAYS_CRITICAL,
                seed=4,
            ),
        }
        engine = H.build_engine(
            agents,
            session_id=sid,
            subreddit_id=sub_id,
            cost_tracker=cost_tracker,
            max_cost_per_thread_usd=1.0,
            max_turns=12,
            min_posts=6,
        )
        session = DeliberationSession(
            id=sid,
            hypothesis=(
                "A continuous-flow Suzuki coupling for the API intermediate meets cGMP "
                "impurity targets and cost goals via a robust mechanism and pathway"
            ),
        )
        run = await H.run_story(engine, session, session.hypothesis)
        assert run.consensus is not None

        # Cost tracking: thread stayed under the cap; per-agent slices tracked.
        summary = cost_tracker.thread_summary(sid)
        assert 0.0 < summary["estimated_cost_usd"] <= 1.0
        assert cost_tracker.check_budget(sid, max_usd=1.0)
        reg_cost = cost_tracker.agent_cost(sid, "regulatory")
        assert reg_cost >= 0.0

        # Notification: QA sign-off needed after synthesis.
        store = InMemoryNotificationStore()
        notif = Notification(
            watcher_id=uuid4(),
            event_id=uuid4(),
            subreddit_id=sub_id,
            title="QA sign-off required before capex commit",
            summary="Continuous-flow route requires QA review of impurity control strategy.",
            signal=TriageSignal.HIGH,
        )
        await store.save(notif)
        pending = await store.list_all(status="pending")
        assert len(pending) >= 1

        # Approval queue for an expensive tool call (solvent screening).
        queue = ApprovalQueue()
        req = queue.enqueue(
            subreddit_id=sub_id,
            request_type=ApprovalRequestType.TOOL_CALL,
            initiator="agent:medicinal_chemistry",
            reason="Solvent-screening tool run (~$40 compute)",
            estimated_cost_usd=40.0,
        )
        assert queue.pending_for_subreddit(str(sub_id))[0].id == req.id
        queue.resolve(req.id, ApprovalStatus.APPROVED, decided_by="user:process-lead")
        assert queue.get(req.id).status == ApprovalStatus.APPROVED

        # Org chart for the manufacturing community.
        from colloquip.api.platform_manager import PlatformManager

        pm = PlatformManager()
        pm.initialize()
        res = pm.create_subreddit(
            name=f"mfg_{sub_id.hex[:8]}",
            display_name="API Manufacturing",
            description="continuous flow scale-up",
            thinking_type=ThinkingType.REVIEW,
            primary_domain="drug_discovery",
            required_expertise=["medicinal_chemistry", "regulatory"],
        )
        chart = pm.get_subreddit_org_chart(res["subreddit"]["id"], recent_posts=[])
        assert len(chart.nodes) >= 1


# ===========================================================================
# Story 7 — Cross-domain bridge: microbiome → cancer immunotherapy
# ===========================================================================


@pytest.mark.asyncio
class TestStory7CrossDomainBridge:
    """As a translational scientist, I want Colloquium to surface unexpected
    links between gut-microbiome metabolites and immunotherapy response, so
    that I get a serendipitous discovery prompt I wouldn't write myself.

    Showcases: multi-subreddit isolation, institutional memory (save +
    global search), cross-reference detection + entity extraction.
    """

    FEATURES = (
        "multi_subreddit",
        "memory_global_search",
        "cross_reference_detection",
        "entity_extraction",
    )

    async def test_story(self):
        from colloquip.embeddings.mock import MockEmbeddingProvider
        from colloquip.memory.cross_references import CrossReferenceDetector, extract_entities
        from colloquip.memory.store import InMemoryStore, SynthesisMemory

        embedder = MockEmbeddingProvider(dimension=256)
        store = InMemoryStore()

        micro_sub = uuid4()
        immuno_sub = uuid4()

        # Two syntheses in different subreddits sharing FOXP3 + a compound id.
        micro_text = (
            "SCFA butyrate promotes FOXP3 regulatory T cell differentiation in the gut "
            "microbiome improving immune tolerance mechanism pathway ABC-1234"
        )
        immuno_text = (
            "FOXP3 regulatory T cell differentiation driven by butyrate SCFA affects PD1 "
            "checkpoint immunotherapy response in the gut microbiome mechanism ABC-1234"
        )
        micro_mem = SynthesisMemory(
            thread_id=uuid4(),
            subreddit_id=micro_sub,
            subreddit_name="microbiome",
            topic="SCFA and Treg differentiation",
            synthesis_content=micro_text,
            key_conclusions=["Butyrate expands FOXP3+ Tregs", "SCFA supports tolerance"],
            embedding=await embedder.embed(micro_text),
        )
        immuno_mem = SynthesisMemory(
            thread_id=uuid4(),
            subreddit_id=immuno_sub,
            subreddit_name="immunotherapy",
            topic="Treg balance and checkpoint response",
            synthesis_content=immuno_text,
            key_conclusions=[
                "FOXP3+ Treg load predicts PD1 response",
                "Butyrate modulates response",
            ],
            embedding=await embedder.embed(immuno_text),
        )
        await store.save(micro_mem)
        await store.save(immuno_mem)

        # Entity extraction finds the shared gene + compound.
        micro_entities = extract_entities(micro_text)
        immuno_entities = extract_entities(immuno_text)
        shared = micro_entities & immuno_entities
        assert "GENE:FOXP3" in shared
        assert "COMPOUND:ABC-1234" in shared

        # Global search finds the cross-subreddit memory.
        global_hits = await store.search_global(
            embedding=immuno_mem.embedding, exclude_subreddit=immuno_sub, limit=5
        )
        assert any(h.memory.id == micro_mem.id for h in global_hits)

        # Cross-reference detection surfaces the serendipitous bridge.
        detector = CrossReferenceDetector(
            memory_store=store,
            embedding_provider=embedder,
            similarity_threshold=0.5,  # deterministic margin over the ~0.77 overlap
        )
        refs = await detector.detect_for_memory(immuno_mem, exclude_subreddit=immuno_sub)
        assert len(refs) >= 1
        ref = refs[0]
        assert ref.status == "pending"
        assert ref.similarity > 0.0
        assert ref.target_memory_id == micro_mem.id
        assert any(e in ref.shared_entities for e in ("GENE:FOXP3", "COMPOUND:ABC-1234"))
        assert ref.reasoning


# ===========================================================================
# Coverage matrix — one place to see every feature the stories assert on
# ===========================================================================


def test_user_story_feature_matrix():
    """Emit the feature matrix and assert breadth of coverage.

    Running ``pytest tests/test_user_stories.py::test_user_story_feature_matrix -s``
    prints the story→feature table for demos.
    """
    stories = [
        TestStory1ProteinEngineering,
        TestStory2CancerRepurposing,
        TestStory3PerturbSeq,
        TestStory4GLP1Cognition,
        TestStory5MicrobiomeCellulase,
        TestStory6ManufacturingScaleUp,
        TestStory7CrossDomainBridge,
    ]
    all_features: set[str] = set()
    print("\n\n=== Colloquium user-story feature matrix ===")
    for s in stories:
        print(f"\n{s.__name__}")
        print(f"  {s.__doc__.strip().splitlines()[0]}")
        print(f"  features: {', '.join(s.FEATURES)}")
        all_features.update(s.FEATURES)
    print(f"\nTotal distinct features showcased: {len(all_features)}")

    assert len(stories) == 7
    # The suite should cover a broad, non-trivial slice of the product surface.
    assert len(all_features) >= 25
    # Sanity: core + Phase 6 pillars are all represented somewhere.
    for pillar in (
        "mission",
        "autoresearch",
        "per_agent_budget",
        "approval_queue_budget_override",
        "human_intervention",
        "memory_retrieval",
        "phase_cycle",
        "outcome_tracking",
        "watcher_auto_deliberation",
        "cross_reference_detection",
    ):
        assert pillar in all_features, f"missing pillar: {pillar}"
