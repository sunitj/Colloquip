"""Tests for outcome tracking and agent calibration."""

from uuid import uuid4

import pytest

from colloquip.feedback.calibration import AgentCalibration
from colloquip.feedback.outcome import (
    InMemoryOutcomeTracker,
    OutcomeReport,
    OutcomeType,
)

SUB_A = uuid4()
SUB_B = uuid4()


def make_outcome(
    thread_id=None,
    subreddit_id=None,
    outcome_type="confirmed",
    agent_assessments=None,
    **kwargs,
) -> OutcomeReport:
    return OutcomeReport(
        thread_id=thread_id or uuid4(),
        subreddit_id=subreddit_id or SUB_A,
        outcome_type=outcome_type,
        summary="Test outcome summary",
        agent_assessments=agent_assessments or {},
        **kwargs,
    )


# --- InMemoryOutcomeTracker ---


class TestInMemoryOutcomeTracker:
    @pytest.fixture
    def tracker(self):
        return InMemoryOutcomeTracker()

    @pytest.mark.asyncio
    async def test_save_and_get(self, tracker):
        outcome = make_outcome()
        await tracker.save_outcome(outcome)
        result = await tracker.get_outcome(outcome.id)
        assert result is not None
        assert result.summary == "Test outcome summary"

    @pytest.mark.asyncio
    async def test_get_nonexistent(self, tracker):
        result = await tracker.get_outcome(uuid4())
        assert result is None

    @pytest.mark.asyncio
    async def test_get_outcomes_for_thread(self, tracker):
        tid = uuid4()
        await tracker.save_outcome(make_outcome(thread_id=tid))
        await tracker.save_outcome(make_outcome(thread_id=tid))
        await tracker.save_outcome(make_outcome())

        results = await tracker.get_outcomes_for_thread(tid)
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_get_outcomes_for_subreddit(self, tracker):
        await tracker.save_outcome(make_outcome(subreddit_id=SUB_A))
        await tracker.save_outcome(make_outcome(subreddit_id=SUB_B))

        results = await tracker.get_outcomes_for_subreddit(SUB_A)
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_list_all(self, tracker):
        for _ in range(5):
            await tracker.save_outcome(make_outcome())
        results = await tracker.list_all()
        assert len(results) == 5


# --- AgentCalibration ---


class TestAgentCalibration:
    @pytest.fixture
    def calibration(self):
        return AgentCalibration(min_outcomes=3)  # Lower for testing

    def test_empty_outcomes(self, calibration):
        report = calibration.compute_calibration("agent_1", [])
        assert report.total_evaluations == 0
        assert report.accuracy == 0.0
        assert not report.is_meaningful

    def test_single_correct(self, calibration):
        outcomes = [
            make_outcome(agent_assessments={"agent_1": "correct"}),
        ]
        report = calibration.compute_calibration("agent_1", outcomes)
        assert report.correct == 1
        assert report.accuracy == 1.0
        assert not report.is_meaningful  # <3 outcomes

    def test_mixed_assessments(self, calibration):
        outcomes = [
            make_outcome(agent_assessments={"agent_1": "correct"}),
            make_outcome(agent_assessments={"agent_1": "correct"}),
            make_outcome(agent_assessments={"agent_1": "incorrect"}),
            make_outcome(agent_assessments={"agent_1": "partial"}),
        ]
        report = calibration.compute_calibration("agent_1", outcomes)
        assert report.correct == 2
        assert report.incorrect == 1
        assert report.partial == 1
        assert report.total_evaluations == 4
        assert report.is_meaningful
        # accuracy = 2 / (2 + 1 + 1) = 0.5
        assert abs(report.accuracy - 0.5) < 0.01

    def test_domain_accuracy(self, calibration):
        outcomes = [
            make_outcome(
                subreddit_id=SUB_A,
                agent_assessments={"agent_1": "correct"},
            ),
            make_outcome(
                subreddit_id=SUB_A,
                agent_assessments={"agent_1": "correct"},
            ),
            make_outcome(
                subreddit_id=SUB_B,
                agent_assessments={"agent_1": "incorrect"},
            ),
        ]
        subreddit_names = {SUB_A: "biology", SUB_B: "chemistry"}
        report = calibration.compute_calibration(
            "agent_1", outcomes, subreddit_names=subreddit_names
        )
        assert report.domain_accuracy["biology"] == 1.0
        assert report.domain_accuracy["chemistry"] == 0.0
        assert report.is_meaningful

    def test_agent_not_in_outcomes(self, calibration):
        outcomes = [
            make_outcome(agent_assessments={"agent_2": "correct"}),
        ]
        report = calibration.compute_calibration("agent_1", outcomes)
        assert report.total_evaluations == 0

    def test_overconfidence_bias(self, calibration):
        outcomes = [
            make_outcome(agent_assessments={"agent_1": "incorrect"}),
            make_outcome(agent_assessments={"agent_1": "incorrect"}),
            make_outcome(agent_assessments={"agent_1": "correct"}),
        ]
        report = calibration.compute_calibration("agent_1", outcomes)
        assert any("overconfident" in b for b in report.systematic_biases)

    def test_compute_overview(self, calibration):
        outcomes = [
            make_outcome(agent_assessments={"agent_1": "correct", "agent_2": "incorrect"}),
            make_outcome(agent_assessments={"agent_1": "correct", "agent_2": "correct"}),
            make_outcome(agent_assessments={"agent_1": "correct"}),
        ]
        overview = calibration.compute_overview(outcomes)
        assert overview.total_outcomes == 3
        assert overview.agents_with_data == 2
        assert len(overview.agent_reports) == 2

    def test_compute_overview_calibrated_count(self, calibration):
        # Need 3+ outcomes for meaningful calibration with min_outcomes=3
        outcomes = [
            make_outcome(agent_assessments={"agent_1": "correct"}),
            make_outcome(agent_assessments={"agent_1": "correct"}),
            make_outcome(agent_assessments={"agent_1": "correct"}),
            make_outcome(agent_assessments={"agent_2": "correct"}),
        ]
        overview = calibration.compute_overview(outcomes)
        assert overview.agents_calibrated == 1  # Only agent_1 has 3+


class TestOutcomeTypes:
    def test_outcome_type_values(self):
        assert OutcomeType.CONFIRMED == "confirmed"
        assert OutcomeType.PARTIALLY_CONFIRMED == "partially_confirmed"
        assert OutcomeType.CONTRADICTED == "contradicted"
        assert OutcomeType.INCONCLUSIVE == "inconclusive"
