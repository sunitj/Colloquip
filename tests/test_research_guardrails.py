"""Tests for research loop guardrails (Phase 3)."""

from uuid import uuid4

import pytest

from colloquip.models import ResearchJob, ResearchJobStatus
from colloquip.research.hypothesis_generator import HypothesisGenerator
from colloquip.research.loop import (
    EARNED_AUTONOMY_THRESHOLD,
    ResearchLoopRunner,
)
from colloquip.research.synthesis_evaluator import SynthesisEvaluator


class MockLLMForHypothesis:
    def __init__(self):
        self._call_count = 0

    async def generate(self, system_prompt, user_prompt, max_tokens=None, **kwargs):
        self._call_count += 1

        class Result:
            content = (
                f"Unique hypothesis {self._call_count} about distinct topic {self._call_count}"
            )

        return Result()


def _good_thread_result():
    return {
        "thread_id": uuid4(),
        "agreements": ["Agreement"],
        "disagreements": [],
        "key_conclusions": ["We recommend investigating further"],
        "synthesis_content": "[PUBMED:123] evidence supports this.",
        "estimated_cost_usd": 0.5,
    }


async def _collect_events(runner, job):
    events = []
    async for event in runner.run(job):
        events.append(event)
    return events


class TestEarnedAutonomy:
    """G2: First N iterations emit confirmation_required events."""

    @pytest.mark.asyncio
    async def test_first_iterations_require_confirmation(self):
        llm = MockLLMForHypothesis()
        generator = HypothesisGenerator(llm)
        evaluator = SynthesisEvaluator()

        async def load_memories(sid):
            return []

        async def load_program(sid):
            return "# Test"

        async def run_thread(sid, hypothesis):
            return _good_thread_result()

        runner = ResearchLoopRunner(
            hypothesis_generator=generator,
            evaluator=evaluator,
            load_memories=load_memories,
            load_program=load_program,
            run_thread=run_thread,
        )

        job = ResearchJob(
            subreddit_id=uuid4(),
            max_iterations=EARNED_AUTONOMY_THRESHOLD + 1,
        )

        events = await _collect_events(runner, job)

        confirmation_events = [e for e in events if e.event_type == "confirmation_required"]
        assert len(confirmation_events) == EARNED_AUTONOMY_THRESHOLD

    @pytest.mark.asyncio
    async def test_no_confirmation_after_threshold(self):
        llm = MockLLMForHypothesis()
        generator = HypothesisGenerator(llm)
        evaluator = SynthesisEvaluator()

        async def load_memories(sid):
            return []

        async def load_program(sid):
            return "# Test"

        async def run_thread(sid, hypothesis):
            return _good_thread_result()

        runner = ResearchLoopRunner(
            hypothesis_generator=generator,
            evaluator=evaluator,
            load_memories=load_memories,
            load_program=load_program,
            run_thread=run_thread,
        )

        job = ResearchJob(
            subreddit_id=uuid4(),
            max_iterations=EARNED_AUTONOMY_THRESHOLD + 2,
        )

        events = await _collect_events(runner, job)

        confirmation_events = [e for e in events if e.event_type == "confirmation_required"]
        # Only first EARNED_AUTONOMY_THRESHOLD iterations get confirmation events
        assert len(confirmation_events) == EARNED_AUTONOMY_THRESHOLD


class TestProgramVersionPinning:
    """G5: Pause when research program is modified mid-job."""

    @pytest.mark.asyncio
    async def test_pauses_on_version_change(self):
        llm = MockLLMForHypothesis()
        generator = HypothesisGenerator(llm)
        evaluator = SynthesisEvaluator()
        version = [1]  # Mutable to simulate version change

        async def load_memories(sid):
            return []

        async def load_program(sid):
            return "# Test"

        async def run_thread(sid, hypothesis):
            # Bump version after first thread
            version[0] = 2
            return _good_thread_result()

        async def load_version(sid):
            return version[0]

        runner = ResearchLoopRunner(
            hypothesis_generator=generator,
            evaluator=evaluator,
            load_memories=load_memories,
            load_program=load_program,
            run_thread=run_thread,
            load_program_version=load_version,
        )

        job = ResearchJob(
            subreddit_id=uuid4(),
            max_iterations=10,
            research_program_version=1,
        )

        events = await _collect_events(runner, job)

        # Should complete 1 iteration then detect version change
        version_events = [e for e in events if e.event_type == "program_version_changed"]
        assert len(version_events) == 1
        assert job.status == ResearchJobStatus.PAUSED

    @pytest.mark.asyncio
    async def test_no_pause_when_version_unchanged(self):
        llm = MockLLMForHypothesis()
        generator = HypothesisGenerator(llm)
        evaluator = SynthesisEvaluator()

        async def load_memories(sid):
            return []

        async def load_program(sid):
            return "# Test"

        async def run_thread(sid, hypothesis):
            return _good_thread_result()

        async def load_version(sid):
            return 1  # Always same version

        runner = ResearchLoopRunner(
            hypothesis_generator=generator,
            evaluator=evaluator,
            load_memories=load_memories,
            load_program=load_program,
            run_thread=run_thread,
            load_program_version=load_version,
        )

        job = ResearchJob(
            subreddit_id=uuid4(),
            max_iterations=2,
            research_program_version=1,
        )

        events = await _collect_events(runner, job)

        version_events = [e for e in events if e.event_type == "program_version_changed"]
        assert len(version_events) == 0
        assert job.status == ResearchJobStatus.COMPLETED


class TestHypothesisDiversityGuard:
    """G3: Reject hypotheses too similar to recent attempts."""

    @pytest.mark.asyncio
    async def test_diversity_guard_retries(self):
        """Test that the diversity guard retries when hypothesis is similar."""

        class RepetitiveLLM:
            """LLM that returns the same hypothesis each time."""

            async def generate(self, system_prompt, user_prompt, max_tokens=None, **kwargs):
                class Result:
                    content = "always the same exact hypothesis about binding affinity"

                return Result()

        generator = HypothesisGenerator(RepetitiveLLM())
        evaluator = SynthesisEvaluator()

        async def load_memories(sid):
            return []

        async def load_program(sid):
            return "# Test"

        async def run_thread(sid, hypothesis):
            return _good_thread_result()

        runner = ResearchLoopRunner(
            hypothesis_generator=generator,
            evaluator=evaluator,
            load_memories=load_memories,
            load_program=load_program,
            run_thread=run_thread,
        )

        job = ResearchJob(
            subreddit_id=uuid4(),
            max_iterations=3,
        )

        # Should still complete — diversity guard falls back after retries
        events = await _collect_events(runner, job)
        assert job.current_iteration > 0

    @pytest.mark.asyncio
    async def test_diverse_hypotheses_not_rejected(self):
        """Test that sufficiently different hypotheses pass the guard."""
        call_count = [0]

        class DiverseLLM:
            async def generate(self, system_prompt, user_prompt, max_tokens=None, **kwargs):
                call_count[0] += 1

                class Result:
                    content = (
                        f"Completely unique topic {call_count[0]} "
                        f"with novel concepts {call_count[0] * 137}"
                    )

                return Result()

        generator = HypothesisGenerator(DiverseLLM())
        evaluator = SynthesisEvaluator()

        async def load_memories(sid):
            return []

        async def load_program(sid):
            return "# Test"

        async def run_thread(sid, hypothesis):
            return _good_thread_result()

        runner = ResearchLoopRunner(
            hypothesis_generator=generator,
            evaluator=evaluator,
            load_memories=load_memories,
            load_program=load_program,
            run_thread=run_thread,
        )

        job = ResearchJob(
            subreddit_id=uuid4(),
            max_iterations=3,
        )

        events = await _collect_events(runner, job)

        # Should complete all iterations without extra retries
        assert job.current_iteration == 3
        # One generate call per iteration (no retries needed)
        assert call_count[0] == 3
