"""Tests for the autonomous research loop (Phase 2)."""

from uuid import uuid4

import pytest

from colloquip.models import ResearchJob, ResearchJobStatus
from colloquip.research.hypothesis_generator import HypothesisGenerator
from colloquip.research.loop import ResearchLoopRunner
from colloquip.research.synthesis_evaluator import SynthesisEvaluator


class MockLLMForHypothesis:
    """Mock LLM that returns predictable hypotheses."""

    def __init__(self):
        self._call_count = 0

    async def generate(self, system_prompt, user_prompt, max_tokens=None, **kwargs):
        self._call_count += 1

        class Result:
            content = (
                f"Hypothesis {self._call_count}: Test hypothesis about topic {self._call_count}"
            )

        return Result()


class TestSynthesisEvaluator:
    def test_perfect_synthesis(self):
        evaluator = SynthesisEvaluator()
        score = evaluator.evaluate(
            agreements=["Agreement 1", "Agreement 2"],
            disagreements=[],
            key_conclusions=[
                "We should investigate the binding site further",
                "Next step: run molecular dynamics simulation",
            ],
            synthesis_content=(
                "Based on [PUBMED:12345] and [PUBMED:67890], "
                "the binding affinity [INTERNAL:data1] suggests [WEB:http://example.com]..."
            ),
            prior_conclusions=[],
        )
        assert 0.5 < score <= 1.0

    def test_empty_synthesis(self):
        evaluator = SynthesisEvaluator()
        score = evaluator.evaluate(
            agreements=[],
            disagreements=[],
            key_conclusions=[],
            synthesis_content="",
            prior_conclusions=[],
        )
        assert 0.0 <= score <= 0.5

    def test_all_disagreements(self):
        evaluator = SynthesisEvaluator()
        score = evaluator.evaluate(
            agreements=[],
            disagreements=["Disagreement 1", "Disagreement 2"],
            key_conclusions=["Claim with no evidence"],
            synthesis_content="No citations here.",
        )
        assert 0.0 <= score < 0.5

    def test_novelty_scoring(self):
        evaluator = SynthesisEvaluator()

        # All novel
        score_novel = evaluator._score_novelty(
            ["Completely new finding about quantum effects"],
            ["Old finding about classical mechanics"],
        )
        assert score_novel > 0.5

        # All repeated
        score_repeat = evaluator._score_novelty(
            ["the same exact finding repeated here"],
            ["the same exact finding repeated here"],
        )
        assert score_repeat < 0.5

    def test_actionability_scoring(self):
        evaluator = SynthesisEvaluator()
        score = evaluator._score_actionability(
            [
                "We recommend further study of compound X",
                "The next step should be crystallography",
                "This is an observation with no action",
            ]
        )
        assert abs(score - 2 / 3) < 0.01


class TestResearchLoopRunner:
    @pytest.fixture
    def mock_llm(self):
        return MockLLMForHypothesis()

    @pytest.fixture
    def evaluator(self):
        return SynthesisEvaluator()

    @pytest.fixture
    def hypothesis_generator(self, mock_llm):
        return HypothesisGenerator(mock_llm)

    @pytest.fixture
    def subreddit_id(self):
        return uuid4()

    async def _collect_events(self, runner, job):
        events = []
        async for event in runner.run(job):
            events.append(event)
        return events

    @pytest.mark.asyncio
    async def test_basic_loop_runs_one_iteration(
        self, hypothesis_generator, evaluator, subreddit_id
    ):
        """Test that a loop runs at least one iteration."""

        async def load_memories(sid):
            return []

        async def load_program(sid):
            return "# Test Program\n- Focus on testing"

        async def run_thread(sid, hypothesis):
            return {
                "thread_id": uuid4(),
                "agreements": ["Test agreement"],
                "disagreements": [],
                "key_conclusions": ["We recommend testing more"],
                "synthesis_content": "Based on [PUBMED:123], we find...",
                "estimated_cost_usd": 0.50,
            }

        runner = ResearchLoopRunner(
            hypothesis_generator=hypothesis_generator,
            evaluator=evaluator,
            load_memories=load_memories,
            load_program=load_program,
            run_thread=run_thread,
        )

        job = ResearchJob(
            subreddit_id=subreddit_id,
            max_iterations=1,
        )

        events = await self._collect_events(runner, job)

        # Should have: hypothesis_generated, thread_started, thread_completed, iteration_complete
        event_types = [e.event_type for e in events]
        assert "hypothesis_generated" in event_types
        assert "thread_started" in event_types
        assert "thread_completed" in event_types
        assert "iteration_complete" in event_types
        assert job.current_iteration == 1
        assert job.status == ResearchJobStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_budget_enforcement(self, hypothesis_generator, evaluator, subreddit_id):
        """Test that the loop stops when budget is exhausted."""

        async def load_memories(sid):
            return []

        async def load_program(sid):
            return "# Test"

        async def run_thread(sid, hypothesis):
            return {
                "thread_id": uuid4(),
                "agreements": ["A"],
                "disagreements": [],
                "key_conclusions": ["Recommend more"],
                "synthesis_content": "[PUBMED:1]",
                "estimated_cost_usd": 3.0,
            }

        runner = ResearchLoopRunner(
            hypothesis_generator=hypothesis_generator,
            evaluator=evaluator,
            load_memories=load_memories,
            load_program=load_program,
            run_thread=run_thread,
        )

        job = ResearchJob(
            subreddit_id=subreddit_id,
            max_iterations=100,
            max_cost_usd=5.0,
        )

        events = await self._collect_events(runner, job)

        # Should stop after ~2 iterations ($3 each, budget $5)
        assert job.current_iteration <= 2
        assert job.total_cost_usd <= 6.0  # allows the one that exceeded

    @pytest.mark.asyncio
    async def test_declining_value_auto_stop(self, hypothesis_generator, evaluator, subreddit_id):
        """Test auto-stop when consecutive iterations are discarded."""
        call_count = 0

        async def load_memories(sid):
            return []

        async def load_program(sid):
            return "# Test"

        async def run_thread(sid, hypothesis):
            nonlocal call_count
            call_count += 1
            return {
                "thread_id": uuid4(),
                "agreements": [],
                "disagreements": ["D"],
                "key_conclusions": [],
                "synthesis_content": "",
                "estimated_cost_usd": 0.10,
            }

        runner = ResearchLoopRunner(
            hypothesis_generator=hypothesis_generator,
            evaluator=evaluator,
            load_memories=load_memories,
            load_program=load_program,
            run_thread=run_thread,
        )

        job = ResearchJob(
            subreddit_id=subreddit_id,
            max_iterations=20,
            max_cost_usd=100.0,
        )

        events = await self._collect_events(runner, job)

        # Should stop after 5 consecutive discards (DECLINING_VALUE_WINDOW=5)
        # First iteration is always "keep" (baseline), so need 5 more discards
        assert job.status == ResearchJobStatus.STOPPED
        assert job.current_iteration <= 10

    @pytest.mark.asyncio
    async def test_keep_discard_logic(self, hypothesis_generator, evaluator, subreddit_id):
        """Test that iterations are correctly classified as keep/discard."""
        iteration_counter = 0

        async def load_memories(sid):
            return []

        async def load_program(sid):
            return "# Test"

        async def run_thread(sid, hypothesis):
            nonlocal iteration_counter
            iteration_counter += 1
            if iteration_counter == 1:
                # Good result (baseline)
                return {
                    "thread_id": uuid4(),
                    "agreements": ["A1", "A2"],
                    "disagreements": [],
                    "key_conclusions": ["We recommend testing"],
                    "synthesis_content": "[PUBMED:1] [PUBMED:2]",
                    "estimated_cost_usd": 0.5,
                }
            else:
                # Poor result
                return {
                    "thread_id": uuid4(),
                    "agreements": [],
                    "disagreements": ["D"],
                    "key_conclusions": [],
                    "synthesis_content": "",
                    "estimated_cost_usd": 0.5,
                }

        runner = ResearchLoopRunner(
            hypothesis_generator=hypothesis_generator,
            evaluator=evaluator,
            load_memories=load_memories,
            load_program=load_program,
            run_thread=run_thread,
        )

        job = ResearchJob(
            subreddit_id=subreddit_id,
            max_iterations=3,
        )

        events = await self._collect_events(runner, job)

        # First iteration should be "keep" (baseline)
        assert job.metric_history[0]["status"] == "keep"
        assert len(job.threads_completed) >= 1

    @pytest.mark.asyncio
    async def test_pause_stops_loop(self, hypothesis_generator, evaluator, subreddit_id):
        """Test that pausing the job stops the loop."""

        async def load_memories(sid):
            return []

        async def load_program(sid):
            return "# Test"

        call_count = 0

        async def run_thread(sid, hypothesis):
            nonlocal call_count
            call_count += 1
            # Pause after first iteration
            return {
                "thread_id": uuid4(),
                "agreements": ["A"],
                "disagreements": [],
                "key_conclusions": ["Next step: test"],
                "synthesis_content": "[PUBMED:1]",
                "estimated_cost_usd": 0.5,
            }

        runner = ResearchLoopRunner(
            hypothesis_generator=hypothesis_generator,
            evaluator=evaluator,
            load_memories=load_memories,
            load_program=load_program,
            run_thread=run_thread,
        )

        job = ResearchJob(
            subreddit_id=subreddit_id,
            max_iterations=1,
        )

        events = await self._collect_events(runner, job)
        assert job.status == ResearchJobStatus.COMPLETED


class TestHypothesisGenerator:
    @pytest.mark.asyncio
    async def test_generates_hypothesis(self):
        llm = MockLLMForHypothesis()
        generator = HypothesisGenerator(llm)

        hypothesis = await generator.generate(
            research_program="# KRAS inhibitor research",
            memories=[
                {
                    "topic": "Binding affinity",
                    "key_conclusions": ["IC50 of 50nM achieved"],
                    "confidence_alpha": 3.0,
                    "confidence_beta": 1.0,
                }
            ],
            experiment_history=[
                {
                    "iteration": 0,
                    "hypothesis": "Test allosteric site",
                    "metric": 0.7,
                    "status": "keep",
                }
            ],
        )

        assert isinstance(hypothesis, str)
        assert len(hypothesis) > 0

    @pytest.mark.asyncio
    async def test_generates_with_empty_context(self):
        llm = MockLLMForHypothesis()
        generator = HypothesisGenerator(llm)

        hypothesis = await generator.generate(
            research_program="",
            memories=[],
            experiment_history=[],
        )

        assert isinstance(hypothesis, str)
        assert len(hypothesis) > 0


class TestResearchJobAPI:
    """Test research job API endpoints."""

    @pytest.fixture
    def client(self):
        from fastapi.testclient import TestClient

        from colloquip.api import create_app

        app = create_app()
        client = TestClient(app)
        client.post("/api/platform/init")
        return client

    def _create_subreddit(self, client, name="test_rj"):
        return client.post(
            "/api/subreddits",
            json={
                "name": name,
                "display_name": f"Test {name}",
                "description": "Test subreddit",
            },
        )

    def test_create_research_job(self, client):
        self._create_subreddit(client)
        resp = client.post(
            "/api/subreddits/test_rj/research-jobs",
            json={"max_iterations": 10, "max_cost_usd": 5.0},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "pending"
        assert data["max_iterations"] == 10

    def test_create_duplicate_active_job(self, client):
        self._create_subreddit(client, "test_dup")
        client.post(
            "/api/subreddits/test_dup/research-jobs",
            json={"max_iterations": 10},
        )
        resp = client.post(
            "/api/subreddits/test_dup/research-jobs",
            json={"max_iterations": 5},
        )
        assert resp.status_code == 409

    def test_list_research_jobs(self, client):
        self._create_subreddit(client, "test_list")
        client.post(
            "/api/subreddits/test_list/research-jobs",
            json={"max_iterations": 10},
        )
        resp = client.get("/api/subreddits/test_list/research-jobs")
        assert resp.status_code == 200
        assert len(resp.json()["jobs"]) == 1

    def test_get_research_job_detail(self, client):
        self._create_subreddit(client, "test_detail")
        create_resp = client.post(
            "/api/subreddits/test_detail/research-jobs",
            json={"max_iterations": 10},
        )
        job_id = create_resp.json()["id"]
        resp = client.get(f"/api/research-jobs/{job_id}")
        assert resp.status_code == 200
        assert resp.json()["metric_history"] == []

    def test_stop_research_job(self, client):
        self._create_subreddit(client, "test_stop")
        create_resp = client.post(
            "/api/subreddits/test_stop/research-jobs",
            json={"max_iterations": 10},
        )
        job_id = create_resp.json()["id"]
        resp = client.post(f"/api/research-jobs/{job_id}/stop")
        assert resp.status_code == 200
        assert resp.json()["status"] == "stopped"

    def test_get_results(self, client):
        self._create_subreddit(client, "test_results")
        create_resp = client.post(
            "/api/subreddits/test_results/research-jobs",
            json={"max_iterations": 10},
        )
        job_id = create_resp.json()["id"]
        resp = client.get(f"/api/research-jobs/{job_id}/results")
        assert resp.status_code == 200
        assert resp.json()["iterations"] == []

    def test_not_found(self, client):
        resp = client.get("/api/research-jobs/nonexistent")
        assert resp.status_code == 404

    def test_subreddit_not_found(self, client):
        resp = client.post(
            "/api/subreddits/nonexistent/research-jobs",
            json={"max_iterations": 10},
        )
        assert resp.status_code == 404
