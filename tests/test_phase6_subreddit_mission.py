"""Phase 6 subreddit mission tests: program.md parsing and prompt injection.

Test-first: drives the implementation of colloquip.subreddit_mission.parse_objectives,
render_mission_for_prompt, and the optional subreddit_mission kwarg on
colloquip.agents.prompts.build_system_prompt.
"""

import pytest

from colloquip.agents.base import BaseDeliberationAgent
from colloquip.agents.prompts import build_system_prompt
from colloquip.llm.mock import MockBehavior, MockLLM
from colloquip.models import (
    AgentConfig,
    AgentDependencies,
    ConversationMetrics,
    DeliberationSession,
    MissionObjective,
    Phase,
    PhaseSignal,
)
from colloquip.subreddit_mission import (
    parse_objectives,
    render_mission_for_prompt,
)


class TestParseObjectives:
    def test_empty_markdown_returns_empty_list(self):
        assert parse_objectives("") == []
        assert parse_objectives(None) == []
        assert parse_objectives("No headings here, just paragraphs.") == []

    def test_parses_h2_objective_headings_with_metric_and_target(self):
        md = (
            "# Oncology Deliberation Mission\n\n"
            "High-stakes drug repurposing decisions.\n\n"
            "## Objective: Reduce false positive claims\n"
            "Cut hallucinated citations in synthesis.\n"
            "- metric: citation_verification_rate\n"
            "- target: 0.85\n\n"
            "## Objective: Improve novelty\n"
            "Surface unexpected mechanisms.\n"
            "- metric: novelty_avg\n"
            "- target: 0.5\n"
        )
        objectives = parse_objectives(md)
        assert len(objectives) == 2

        first = objectives[0]
        assert first.title == "Reduce false positive claims"
        assert first.metric == "citation_verification_rate"
        assert first.target == 0.85
        assert "Cut hallucinated citations" in first.description

        second = objectives[1]
        assert second.title == "Improve novelty"
        assert second.metric == "novelty_avg"
        assert second.target == 0.5

    def test_qualitative_objective_without_metric_bullets(self):
        md = (
            "## Objective: Build trust with clinicians\n"
            "We want expert users to rely on our output.\n"
        )
        objectives = parse_objectives(md)
        assert len(objectives) == 1
        assert objectives[0].metric is None
        assert objectives[0].target is None
        assert "trust with clinicians" in objectives[0].title.lower()

    def test_ignores_non_objective_headings(self):
        md = (
            "## Background\n"
            "Context paragraph.\n\n"
            "## Objective: Real goal\n"
            "- metric: foo\n"
            "- target: 0.1\n"
        )
        objectives = parse_objectives(md)
        assert len(objectives) == 1
        assert objectives[0].title == "Real goal"

    def test_objective_ids_are_stable_and_unique(self):
        md = "## Objective: First\n## Objective: Second\n## Objective: Third\n"
        objectives = parse_objectives(md)
        ids = [o.id for o in objectives]
        assert len(set(ids)) == 3


class TestRenderMissionForPrompt:
    def test_renders_empty_when_no_mission(self):
        assert render_mission_for_prompt(None, []) == ""
        assert render_mission_for_prompt("", []) == ""

    def test_renders_mission_header_and_objectives(self):
        md = "# Mission\n\nCore intent."
        objectives = [
            MissionObjective(
                id="obj-1",
                title="Reduce noise",
                metric="noise",
                target=0.1,
            )
        ]
        rendered = render_mission_for_prompt(md, objectives)
        assert "## Subreddit Mission" in rendered
        assert "Core intent." in rendered
        assert "Reduce noise" in rendered
        assert "noise" in rendered
        assert "0.1" in rendered

    def test_truncates_long_mission_to_soft_cap(self):
        md = "# Mission\n\n" + ("very long ramble. " * 2000)
        rendered = render_mission_for_prompt(md, [], max_chars=1200)
        assert len(rendered) <= 1500  # allow small header overhead
        assert "..." in rendered or "[truncated]" in rendered


class TestBuildSystemPromptWithMission:
    def _make_config(self) -> AgentConfig:
        return AgentConfig(
            agent_id="adm-et-expert",
            display_name="ADMET Expert",
            persona_prompt="You are an ADMET expert.",
            phase_mandates={Phase.EXPLORE: ""},
            domain_keywords=["pk", "admet"],
            knowledge_scope=["pharmacokinetics"],
        )

    def test_build_system_prompt_without_mission_has_no_mission_header(self):
        config = self._make_config()
        prompt = build_system_prompt(config, Phase.EXPLORE)
        assert "## Subreddit Mission" not in prompt
        assert "ADMET expert" in prompt

    def test_build_system_prompt_with_mission_prepends_header(self):
        config = self._make_config()
        mission_md = "# Mission\n\nImprove PK predictions."
        objectives = [
            MissionObjective(
                id="obj-1",
                title="Cut error below 30%",
                metric="mae",
                target=0.3,
            )
        ]
        prompt = build_system_prompt(
            config,
            Phase.EXPLORE,
            subreddit_mission=mission_md,
            mission_objectives=objectives,
        )
        # Mission should appear before persona for top-of-prompt priming
        mission_idx = prompt.find("## Subreddit Mission")
        persona_idx = prompt.find("ADMET expert")
        assert mission_idx != -1
        assert persona_idx != -1
        assert mission_idx < persona_idx
        assert "Improve PK predictions" in prompt
        assert "Cut error below 30%" in prompt


class _SpyLLM:
    """Wraps MockLLM to capture the system_prompt it was called with."""

    def __init__(self):
        self.inner = MockLLM(behavior=MockBehavior.MIXED, seed=1)
        self.last_system_prompt: str = ""
        self.last_user_prompt: str = ""

    async def generate(self, system_prompt, user_prompt, max_tokens=None):
        self.last_system_prompt = system_prompt
        self.last_user_prompt = user_prompt
        return await self.inner.generate(system_prompt, user_prompt, max_tokens)


@pytest.mark.asyncio
class TestGeneratePostPropagatesMission:
    async def test_generate_post_injects_mission_into_system_prompt(self):
        config = AgentConfig(
            agent_id="adm-et-expert",
            display_name="ADMET Expert",
            persona_prompt="You are an ADMET expert.",
            phase_mandates={Phase.EXPLORE: ""},
            domain_keywords=["pk"],
            knowledge_scope=["pharmacokinetics"],
        )
        llm = _SpyLLM()
        agent = BaseDeliberationAgent(config=config, llm=llm)
        session = DeliberationSession(hypothesis="GLP-1 improves cognition")
        signal = PhaseSignal(
            current_phase=Phase.EXPLORE,
            confidence=0.9,
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
        mission = "# Mission\n\nReduce hallucinations."
        objectives = [
            MissionObjective(
                id="obj-1",
                title="Verify every citation",
                metric="citation_verification_rate",
                target=0.9,
            )
        ]
        deps = AgentDependencies(
            session=session,
            phase=Phase.EXPLORE,
            phase_signal=signal,
            posts=[],
            subreddit_mission=mission,
            mission_objectives=objectives,
        )
        await agent.generate_post(deps)

        assert "## Subreddit Mission" in llm.last_system_prompt
        assert "Reduce hallucinations" in llm.last_system_prompt
        assert "Verify every citation" in llm.last_system_prompt
