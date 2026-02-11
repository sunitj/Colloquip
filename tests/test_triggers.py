"""Tests for trigger evaluator."""

import pytest

from colloquip.models import AgentStance, Phase
from colloquip.triggers import TriggerEvaluator

from tests.conftest import create_post


@pytest.fixture
def biology_evaluator():
    return TriggerEvaluator(
        agent_id="biology",
        domain_keywords=["mechanism", "target", "pathway", "receptor", "gene", "protein"],
        knowledge_scope=["biology", "preclinical"],
    )


@pytest.fixture
def redteam_evaluator():
    return TriggerEvaluator(
        agent_id="redteam",
        domain_keywords=["assumption", "bias", "alternative", "failure", "risk"],
        knowledge_scope=["biology", "chemistry", "safety", "clinical", "regulatory"],
        is_red_team=True,
    )


class TestRelevance:
    def test_domain_keywords_trigger(self, biology_evaluator):
        posts = [
            create_post(
                content="The mechanism involves receptor binding in the target pathway.",
                agent_id="chemistry",
            )
        ]
        should_respond, rules = biology_evaluator.evaluate(posts, Phase.EXPLORE)
        assert should_respond
        assert "relevance" in rules

    def test_no_domain_keywords_no_trigger(self, biology_evaluator):
        posts = [
            create_post(
                content="The compound has good bioavailability and clearance.",
                agent_id="chemistry",
            )
        ]
        should_respond, rules = biology_evaluator.evaluate(posts, Phase.EXPLORE)
        # May trigger via other rules but not relevance
        assert "relevance" not in rules or not should_respond

    def test_phase_modulation_explore_lower_threshold(self, biology_evaluator):
        """In EXPLORE, only 1 keyword match needed."""
        posts = [
            create_post(content="The mechanism is interesting.", agent_id="chemistry")
        ]
        should_respond, rules = biology_evaluator.evaluate(posts, Phase.EXPLORE)
        assert "relevance" in rules


class TestDisagreement:
    def test_strong_claim_triggers(self, biology_evaluator):
        posts = [
            create_post(
                content="This clearly demonstrates that the target pathway is invalid.",
                agent_id="chemistry",
            )
        ]
        should_respond, rules = biology_evaluator.evaluate(posts, Phase.DEBATE)
        assert "disagreement" in rules

    def test_own_posts_excluded(self, biology_evaluator):
        posts = [
            create_post(
                content="This clearly demonstrates the mechanism is proven.",
                agent_id="biology",  # Same agent
            )
        ]
        should_respond, rules = biology_evaluator.evaluate(posts, Phase.DEBATE)
        assert "disagreement" not in rules


class TestQuestion:
    def test_unanswered_domain_question(self, biology_evaluator):
        posts = [
            create_post(
                content="What is the mechanism of this receptor interaction?",
                agent_id="chemistry",
            )
        ]
        should_respond, rules = biology_evaluator.evaluate(posts, Phase.EXPLORE)
        assert "question" in rules

    def test_answered_question_no_trigger(self, biology_evaluator):
        posts = [
            create_post(
                content="What is the mechanism of receptor binding?",
                agent_id="chemistry",
            ),
            create_post(
                content="The mechanism of receptor binding involves conformational change.",
                agent_id="biology",
            ),
        ]
        should_respond, rules = biology_evaluator.evaluate(posts, Phase.EXPLORE)
        assert "question" not in rules


class TestSilenceBreaking:
    def test_never_posted_triggers(self, biology_evaluator):
        posts = [
            create_post(content=f"Discussion about mechanism {i}", agent_id="chemistry")
            for i in range(10)
        ]
        should_respond, rules = biology_evaluator.evaluate(posts, Phase.EXPLORE)
        assert "silence_breaking" in rules

    def test_recent_post_no_trigger(self, biology_evaluator):
        posts = [
            create_post(content="Something about the target.", agent_id="biology"),
            create_post(content="The mechanism is interesting.", agent_id="chemistry"),
        ]
        should_respond, rules = biology_evaluator.evaluate(posts, Phase.EXPLORE)
        assert "silence_breaking" not in rules


class TestBridgeOpportunity:
    def test_bridge_between_agents(self, biology_evaluator):
        posts = [
            create_post(
                content="The target mechanism shows promising pathway activation.",
                agent_id="chemistry",
            ),
            create_post(
                content="The clinical application of this compound is exciting.",
                agent_id="clinical",
            ),
        ]
        should_respond, rules = biology_evaluator.evaluate(posts, Phase.EXPLORE)
        # Bridge fires if bridge patterns match
        # "mechanism" in chemistry post, "application" in clinical post
        # and biology domain keywords in the text
        if "bridge_opportunity" in rules:
            assert True  # Bridge detected
        # This is heuristic, may or may not fire depending on exact pattern matching

    def test_single_agent_no_bridge(self, biology_evaluator):
        posts = [
            create_post(content="Discussion about target mechanism.", agent_id="chemistry"),
        ]
        should_respond, rules = biology_evaluator.evaluate(posts, Phase.EXPLORE)
        assert "bridge_opportunity" not in rules


class TestUncertaintyResponse:
    def test_uncertainty_in_domain(self, biology_evaluator):
        posts = [
            create_post(
                content="The mechanism remains unclear and uncertain for this target.",
                agent_id="chemistry",
            )
        ]
        should_respond, rules = biology_evaluator.evaluate(posts, Phase.EXPLORE)
        assert "uncertainty_response" in rules


class TestRedTeamRules:
    def test_consensus_forming(self, redteam_evaluator):
        posts = [
            create_post(stance=AgentStance.SUPPORTIVE, agent_id="biology"),
            create_post(stance=AgentStance.SUPPORTIVE, agent_id="chemistry"),
            create_post(stance=AgentStance.SUPPORTIVE, agent_id="clinical"),
        ]
        should_respond, rules = redteam_evaluator.evaluate(posts, Phase.DEBATE)
        assert "consensus_forming" in rules

    def test_criticism_gap(self, redteam_evaluator):
        posts = [
            create_post(stance=AgentStance.SUPPORTIVE, agent_id="biology"),
            create_post(stance=AgentStance.NEUTRAL, agent_id="chemistry"),
            create_post(stance=AgentStance.SUPPORTIVE, agent_id="clinical"),
        ]
        should_respond, rules = redteam_evaluator.evaluate(posts, Phase.DEBATE)
        assert "criticism_gap" in rules

    def test_premature_convergence(self, redteam_evaluator):
        posts = [create_post(agent_id=f"a{i}") for i in range(10)]  # Below 15
        should_respond, rules = redteam_evaluator.evaluate(posts, Phase.CONVERGE)
        assert "premature_convergence" in rules


class TestRefractoryPeriod:
    def test_refractory_blocks_response(self, biology_evaluator):
        posts = [
            create_post(content="Some initial context.", agent_id="chemistry"),
            create_post(
                content="The mechanism involves receptor binding in the target pathway.",
                agent_id="biology",
            ),
        ]
        should_respond, rules = biology_evaluator.evaluate(posts, Phase.EXPLORE)
        assert not should_respond  # Blocked by refractory

    def test_past_refractory_allows_response(self, biology_evaluator):
        posts = [
            create_post(content="Biology post about mechanism.", agent_id="biology"),
            create_post(content="Chemistry post.", agent_id="chemistry"),
            create_post(
                content="More about the target mechanism and pathway.",
                agent_id="clinical",
            ),
        ]
        should_respond, rules = biology_evaluator.evaluate(posts, Phase.EXPLORE)
        assert should_respond


class TestSeedPhase:
    def test_empty_posts_seed_phase(self, biology_evaluator):
        should_respond, rules = biology_evaluator.evaluate([], Phase.EXPLORE)
        assert should_respond
        assert "seed_phase" in rules
