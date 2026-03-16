"""Research loop runner: autonomous deliberation iteration loop.

Inspired by Karpathy's autoresearch pattern:
  deliberate → evaluate → keep/discard → generate next hypothesis → repeat.
"""

import logging
from datetime import datetime, timezone
from typing import Any, AsyncIterator, Callable, Coroutine, Dict, List, Optional
from uuid import UUID

from colloquip.models import (
    ResearchJob,
    ResearchJobEvent,
    ResearchJobStatus,
)
from colloquip.research.hypothesis_generator import HypothesisGenerator
from colloquip.research.synthesis_evaluator import SynthesisEvaluator

logger = logging.getLogger(__name__)

# Type for callbacks
MemoryLoader = Callable[[UUID], Coroutine[Any, Any, List[Dict[str, Any]]]]
ProgramLoader = Callable[[UUID], Coroutine[Any, Any, Optional[str]]]
ThreadRunner = Callable[[UUID, str], Coroutine[Any, Any, Dict[str, Any]]]
JobPersister = Callable[[ResearchJob], Coroutine[Any, Any, None]]
ProgramVersionLoader = Callable[[UUID], Coroutine[Any, Any, int]]

# Constants
DECLINING_VALUE_WINDOW = 5  # Stop after N consecutive discards
EARNED_AUTONOMY_THRESHOLD = 3  # Human confirmation required for first N iterations
DIVERSITY_SIMILARITY_THRESHOLD = 0.85  # Reject hypotheses with overlap > this
MAX_DIVERSITY_RETRIES = 3  # Retry hypothesis generation if too similar


class ResearchLoopRunner:
    """Autonomous research iteration loop.

    Loop:
    1. Load research program + synthesis memories from prior iterations
    2. Generate next hypothesis (via LLM, informed by what worked/didn't)
    3. Create thread, run deliberation
    4. Evaluate synthesis quality (composite metric)
    5. Keep or discard based on whether it advances understanding
    6. Record to results log
    7. Repeat until budget/iteration limit/human stop
    """

    def __init__(
        self,
        hypothesis_generator: HypothesisGenerator,
        evaluator: SynthesisEvaluator,
        load_memories: MemoryLoader,
        load_program: ProgramLoader,
        run_thread: ThreadRunner,
        persist_job: Optional[JobPersister] = None,
        load_program_version: Optional[ProgramVersionLoader] = None,
    ):
        self.hypothesis_generator = hypothesis_generator
        self.evaluator = evaluator
        self._load_memories = load_memories
        self._load_program = load_program
        self._run_thread = run_thread
        self._persist_job = persist_job
        self._load_program_version = load_program_version

    async def run(self, job: ResearchJob) -> AsyncIterator[ResearchJobEvent]:
        """Run the research loop, yielding events for each step."""
        job.status = ResearchJobStatus.RUNNING
        job.started_at = datetime.now(timezone.utc)

        try:
            async for event in self._loop(job):
                yield event
        except Exception as e:
            logger.error("Research loop failed for job %s: %s", job.id, e)
            job.status = ResearchJobStatus.FAILED
            yield ResearchJobEvent(
                job_id=job.id,
                event_type="failed",
                iteration=job.current_iteration,
                data={"error": str(e)},
            )
        finally:
            if job.status == ResearchJobStatus.RUNNING:
                job.status = ResearchJobStatus.COMPLETED
            job.updated_at = datetime.now(timezone.utc)
            if self._persist_job:
                await self._persist_job(job)

    async def _loop(self, job: ResearchJob) -> AsyncIterator[ResearchJobEvent]:
        """Inner loop with budget and termination checks."""
        while not self._should_stop(job):
            # G5: Research program version pinning
            if self._load_program_version:
                current_version = await self._load_program_version(job.subreddit_id)
                if current_version != job.research_program_version:
                    job.status = ResearchJobStatus.PAUSED
                    yield ResearchJobEvent(
                        job_id=job.id,
                        event_type="program_version_changed",
                        iteration=job.current_iteration,
                        data={
                            "original_version": job.research_program_version,
                            "current_version": current_version,
                            "message": (
                                "Research program updated. Resume with new program "
                                "or continue with original?"
                            ),
                        },
                    )
                    break

            # G2: Earned autonomy — first N iterations require confirmation
            if job.current_iteration < EARNED_AUTONOMY_THRESHOLD:
                yield ResearchJobEvent(
                    job_id=job.id,
                    event_type="confirmation_required",
                    iteration=job.current_iteration,
                    data={
                        "message": (
                            f"Iteration {job.current_iteration + 1} of "
                            f"{EARNED_AUTONOMY_THRESHOLD} requiring confirmation. "
                            "After this threshold, the loop runs autonomously."
                        ),
                    },
                )

            # 1. Load context
            program = await self._load_program(job.subreddit_id)
            memories = await self._load_memories(job.subreddit_id)

            # 2. Generate hypothesis with diversity guard
            hypothesis = await self._generate_diverse_hypothesis(job, program or "", memories)
            yield ResearchJobEvent(
                job_id=job.id,
                event_type="hypothesis_generated",
                iteration=job.current_iteration,
                data={"hypothesis": hypothesis},
            )

            # 3. Run deliberation
            yield ResearchJobEvent(
                job_id=job.id,
                event_type="thread_started",
                iteration=job.current_iteration,
                data={"hypothesis": hypothesis},
            )
            thread_result = await self._run_thread(job.subreddit_id, hypothesis)
            thread_id = thread_result.get("thread_id")

            yield ResearchJobEvent(
                job_id=job.id,
                event_type="thread_completed",
                iteration=job.current_iteration,
                data={
                    "thread_id": str(thread_id) if thread_id else None,
                    "hypothesis": hypothesis,
                },
            )

            # 4. Evaluate
            metric = self.evaluator.evaluate(
                agreements=thread_result.get("agreements", []),
                disagreements=thread_result.get("disagreements", []),
                key_conclusions=thread_result.get("key_conclusions", []),
                synthesis_content=thread_result.get("synthesis_content", ""),
                prior_conclusions=self._collect_prior_conclusions(memories),
            )

            # Set baseline on first iteration
            if job.baseline_metric is None:
                job.baseline_metric = metric

            # 5. Keep or discard
            if self._is_improvement(metric, job):
                job.best_metric = metric
                if thread_id:
                    job.threads_completed.append(thread_id)
                status = "keep"
            else:
                if thread_id:
                    job.threads_discarded.append(thread_id)
                status = "discard"

            # 6. Record
            cost = thread_result.get("estimated_cost_usd", 0.0)
            job.total_cost_usd += cost
            job.metric_history.append(
                {
                    "iteration": job.current_iteration,
                    "thread_id": str(thread_id) if thread_id else None,
                    "hypothesis": hypothesis,
                    "metric": metric,
                    "status": status,
                    "cost_usd": cost,
                }
            )
            job.current_iteration += 1
            job.updated_at = datetime.now(timezone.utc)

            yield ResearchJobEvent(
                job_id=job.id,
                event_type="iteration_complete",
                iteration=job.current_iteration - 1,
                data={
                    "metric": metric,
                    "status": status,
                    "best_metric": job.best_metric,
                    "total_cost_usd": job.total_cost_usd,
                },
            )

            # Persist after each iteration
            if self._persist_job:
                await self._persist_job(job)

    def _should_stop(self, job: ResearchJob) -> bool:
        """Check all termination conditions."""
        if job.status != ResearchJobStatus.RUNNING:
            return True

        if job.current_iteration >= job.max_iterations:
            logger.info("Job %s: max iterations reached", job.id)
            return True

        if job.total_cost_usd >= job.max_cost_usd:
            logger.info("Job %s: budget exhausted ($%.2f)", job.id, job.total_cost_usd)
            return True

        if job.started_at:
            runtime_hours = (datetime.now(timezone.utc) - job.started_at).total_seconds() / 3600
            if runtime_hours >= job.max_runtime_hours:
                logger.info("Job %s: runtime limit reached", job.id)
                return True

        # Declining value detection
        if self._should_auto_stop(job):
            logger.info("Job %s: declining value detected, auto-stopping", job.id)
            job.status = ResearchJobStatus.STOPPED
            return True

        return False

    def _should_auto_stop(self, job: ResearchJob) -> bool:
        """Stop if last N iterations all discarded (no progress)."""
        if len(job.metric_history) < DECLINING_VALUE_WINDOW:
            return False
        recent = job.metric_history[-DECLINING_VALUE_WINDOW:]
        return all(r["status"] == "discard" for r in recent)

    def _is_improvement(self, metric: float, job: ResearchJob) -> bool:
        """Determine if a metric represents an improvement worth keeping.

        Keep if:
        - It's the first iteration (baseline)
        - Metric is >= 90% of the current best (allows near-equal results)
        - Metric exceeds 0.3 absolute (has meaningful content)
        """
        if job.best_metric is None:
            return True
        if metric >= job.best_metric * 0.9 and metric >= 0.3:
            return True
        return False

    def _collect_prior_conclusions(self, memories: List[Dict[str, Any]]) -> List[str]:
        """Extract all prior conclusions from memories for novelty scoring."""
        conclusions = []
        for mem in memories:
            conclusions.extend(mem.get("key_conclusions", []))
        return conclusions

    async def _generate_diverse_hypothesis(
        self,
        job: ResearchJob,
        program: str,
        memories: List[Dict[str, Any]],
    ) -> str:
        """Generate a hypothesis, retrying if too similar to recent attempts.

        Uses word-overlap similarity as a lightweight diversity check.
        """
        recent_hypotheses = [
            entry["hypothesis"] for entry in job.metric_history[-10:] if "hypothesis" in entry
        ]

        for attempt in range(MAX_DIVERSITY_RETRIES):
            hypothesis = await self.hypothesis_generator.generate(
                research_program=program,
                memories=memories,
                experiment_history=job.metric_history,
            )

            if not recent_hypotheses:
                return hypothesis

            # Check similarity via word overlap
            is_diverse = True
            hyp_words = set(hypothesis.lower().split())
            for prior in recent_hypotheses:
                prior_words = set(prior.lower().split())
                if not hyp_words or not prior_words:
                    continue
                overlap = len(hyp_words & prior_words) / max(
                    min(len(hyp_words), len(prior_words)), 1
                )
                if overlap > DIVERSITY_SIMILARITY_THRESHOLD:
                    is_diverse = False
                    logger.info(
                        "Job %s: hypothesis too similar (%.2f overlap), retrying (%d/%d)",
                        job.id,
                        overlap,
                        attempt + 1,
                        MAX_DIVERSITY_RETRIES,
                    )
                    break

            if is_diverse:
                return hypothesis

        # If all retries exhausted, use the last generated hypothesis anyway
        logger.warning(
            "Job %s: could not generate diverse hypothesis after %d retries",
            job.id,
            MAX_DIVERSITY_RETRIES,
        )
        return hypothesis
