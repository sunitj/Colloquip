"""Job manager: orchestrates pipeline lifecycle from proposal to results.

Handles:
- Creating action proposals for pipeline launches
- Approving proposals and submitting jobs
- Monitoring running jobs via background polling
- Posting results back into threads
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Callable, Coroutine, Dict, List, Optional
from uuid import UUID, uuid4

from colloquip.jobs.executor import BaseExecutor
from colloquip.jobs.pipeline_builder import PipelineBuilder
from colloquip.models import (
    ActionProposal,
    ActionProposalStatus,
    Job,
    JobStatus,
    PipelineDefinition,
)

logger = logging.getLogger(__name__)

# Type for the callback that posts results into a deliberation thread
ResultCallback = Callable[[UUID, Job], Coroutine[Any, Any, None]]


class JobManager:
    """Manages the lifecycle of computational jobs.

    Coordinates between the pipeline builder, executor, and deliberation
    engine to provide a seamless experience for agent-proposed pipelines.
    """

    def __init__(
        self,
        executor: BaseExecutor,
        pipeline_builder: PipelineBuilder,
        work_dir: str = "./work",
        poll_interval_seconds: int = 30,
        max_concurrent_jobs: int = 3,
        auto_approve: bool = False,
    ):
        self.executor = executor
        self.pipeline_builder = pipeline_builder
        self.work_dir = work_dir
        self.poll_interval_seconds = poll_interval_seconds
        self.max_concurrent_jobs = max_concurrent_jobs
        self.auto_approve = auto_approve

        # In-memory state (backed by DB in production)
        self._jobs: Dict[UUID, Job] = {}
        self._proposals: Dict[UUID, ActionProposal] = {}
        self._result_callback: Optional[ResultCallback] = None
        self._running = False
        self._monitor_task: Optional[asyncio.Task] = None

    def set_result_callback(self, callback: ResultCallback):
        """Set the callback for posting job results into threads."""
        self._result_callback = callback

    # ---- Proposals ----

    async def propose_job(
        self,
        agent_id: str,
        session_id: UUID,
        pipeline: PipelineDefinition,
        rationale: str = "",
        thread_id: Optional[UUID] = None,
        compute_profile: str = "standard",
    ) -> ActionProposal:
        """Create an action proposal for a pipeline launch.

        If auto_approve is enabled, immediately submits the job.
        """
        proposal = ActionProposal(
            id=uuid4(),
            session_id=session_id,
            thread_id=thread_id,
            agent_id=agent_id,
            action_type="launch_pipeline",
            description=f"Launch pipeline: {pipeline.name}",
            rationale=rationale,
            proposed_pipeline=pipeline,
            proposed_params={"compute_profile": compute_profile},
        )

        self._proposals[proposal.id] = proposal

        if self.auto_approve:
            await self.approve_proposal(proposal.id, reviewer="auto")

        return proposal

    async def approve_proposal(
        self,
        proposal_id: UUID,
        reviewer: str = "system",
        note: str = "",
    ) -> Optional[Job]:
        """Approve a proposal and submit the job."""
        proposal = self._proposals.get(proposal_id)
        if not proposal:
            logger.warning("Proposal %s not found", proposal_id)
            return None

        if proposal.status != ActionProposalStatus.PENDING:
            logger.warning("Proposal %s is not pending (status: %s)", proposal_id, proposal.status)
            return None

        proposal.status = ActionProposalStatus.APPROVED
        proposal.reviewed_by = reviewer
        proposal.review_note = note
        proposal.reviewed_at = datetime.now(timezone.utc)

        if not proposal.proposed_pipeline:
            logger.error("Approved proposal %s has no pipeline", proposal_id)
            return None

        # Submit the job
        job = await self.submit_job(
            session_id=proposal.session_id,
            thread_id=proposal.thread_id,
            agent_id=proposal.agent_id,
            pipeline=proposal.proposed_pipeline,
            compute_profile=proposal.proposed_params.get("compute_profile", "standard"),
        )
        return job

    async def reject_proposal(
        self,
        proposal_id: UUID,
        reviewer: str = "system",
        note: str = "",
    ) -> None:
        """Reject a proposal."""
        proposal = self._proposals.get(proposal_id)
        if not proposal:
            return
        proposal.status = ActionProposalStatus.REJECTED
        proposal.reviewed_by = reviewer
        proposal.review_note = note
        proposal.reviewed_at = datetime.now(timezone.utc)

    # ---- Jobs ----

    async def submit_job(
        self,
        session_id: UUID,
        agent_id: str,
        pipeline: PipelineDefinition,
        compute_profile: str = "standard",
        thread_id: Optional[UUID] = None,
    ) -> Job:
        """Submit a pipeline for execution."""
        # Validate the pipeline
        errors = self.pipeline_builder.validate_pipeline(pipeline)
        if errors:
            logger.error("Pipeline validation failed: %s", errors)
            job = Job(
                session_id=session_id,
                thread_id=thread_id,
                agent_id=agent_id,
                pipeline=pipeline,
                compute_profile=compute_profile,
                status=JobStatus.FAILED,
                error_message=f"Pipeline validation failed: {'; '.join(errors)}",
            )
            self._jobs[job.id] = job
            return job

        # Check concurrent job limit
        running_count = sum(
            1 for j in self._jobs.values() if j.status in (JobStatus.SUBMITTED, JobStatus.RUNNING)
        )
        if running_count >= self.max_concurrent_jobs:
            job = Job(
                session_id=session_id,
                thread_id=thread_id,
                agent_id=agent_id,
                pipeline=pipeline,
                compute_profile=compute_profile,
                status=JobStatus.FAILED,
                error_message=(
                    f"Maximum concurrent jobs ({self.max_concurrent_jobs}) reached. "
                    "Please wait for existing jobs to complete."
                ),
            )
            self._jobs[job.id] = job
            return job

        # Generate the Nextflow script
        script_content = self.pipeline_builder.generate_nextflow_script(pipeline)
        job_work_dir = f"{self.work_dir}/{pipeline.id}"

        import os

        os.makedirs(job_work_dir, exist_ok=True)
        script_path = f"{job_work_dir}/main.nf"
        with open(script_path, "w") as f:
            f.write(script_content)

        # Submit to executor
        try:
            run_id = await self.executor.submit(
                script_path=script_path,
                profile=compute_profile,
                work_dir=job_work_dir,
                params=pipeline.parameters,
            )

            job = Job(
                session_id=session_id,
                thread_id=thread_id,
                agent_id=agent_id,
                pipeline=pipeline,
                compute_profile=compute_profile,
                status=JobStatus.SUBMITTED,
                nextflow_run_id=run_id,
                submitted_at=datetime.now(timezone.utc),
            )
        except Exception as e:
            logger.error("Failed to submit pipeline: %s", e)
            job = Job(
                session_id=session_id,
                thread_id=thread_id,
                agent_id=agent_id,
                pipeline=pipeline,
                compute_profile=compute_profile,
                status=JobStatus.FAILED,
                error_message=f"Submission failed: {e}",
            )

        self._jobs[job.id] = job
        return job

    async def get_job(self, job_id: UUID) -> Optional[Job]:
        """Get a job by ID."""
        return self._jobs.get(job_id)

    async def list_jobs(self, session_id: UUID) -> List[Job]:
        """List all jobs for a session."""
        return [j for j in self._jobs.values() if j.session_id == session_id]

    async def cancel_job(self, job_id: UUID) -> bool:
        """Cancel a running job."""
        job = self._jobs.get(job_id)
        if not job or not job.nextflow_run_id:
            return False
        if job.status not in (JobStatus.SUBMITTED, JobStatus.RUNNING):
            return False

        cancelled = await self.executor.cancel(job.nextflow_run_id)
        if cancelled:
            job.status = JobStatus.CANCELLED
            job.completed_at = datetime.now(timezone.utc)
        return cancelled

    # ---- Monitoring ----

    async def start_monitor(self):
        """Start the background job monitoring loop."""
        if self._running:
            return
        self._running = True
        self._monitor_task = asyncio.create_task(self._monitor_loop())
        logger.info("Job monitor started (poll every %ds)", self.poll_interval_seconds)

    async def stop_monitor(self):
        """Stop the background job monitoring loop."""
        self._running = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
            self._monitor_task = None
        logger.info("Job monitor stopped")

    async def _monitor_loop(self):
        """Background loop that polls running jobs for status updates."""
        while self._running:
            try:
                await self._poll_running_jobs()
            except Exception as e:
                logger.error("Job monitor error: %s", e)
            await asyncio.sleep(self.poll_interval_seconds)

    async def _poll_running_jobs(self):
        """Check status of all running/submitted jobs."""
        active_jobs = [
            j for j in self._jobs.values() if j.status in (JobStatus.SUBMITTED, JobStatus.RUNNING)
        ]

        for job in active_jobs:
            if not job.nextflow_run_id:
                continue

            try:
                status, message = await self.executor.poll_status(job.nextflow_run_id)

                if status != job.status:
                    old_status = job.status
                    job.status = status
                    logger.info(
                        "Job %s status: %s -> %s (%s)",
                        job.id,
                        old_status.value,
                        status.value,
                        message,
                    )

                    if status == JobStatus.COMPLETED:
                        await self._handle_completion(job)
                    elif status == JobStatus.FAILED:
                        job.error_message = message
                        job.completed_at = datetime.now(timezone.utc)

            except Exception as e:
                logger.error("Error polling job %s: %s", job.id, e)

    async def _handle_completion(self, job: Job):
        """Handle a completed job: gather artifacts and notify."""
        job.completed_at = datetime.now(timezone.utc)

        # Retrieve artifacts
        try:
            work_dir = f"{self.work_dir}/{job.pipeline.id}"
            artifacts = await self.executor.get_results(job.nextflow_run_id, work_dir)
            job.result_artifacts = artifacts

            artifact_summary = ", ".join(f"{a.name} ({a.artifact_type})" for a in artifacts)
            job.result_summary = (
                f"Pipeline '{job.pipeline.name}' completed successfully. "
                f"Artifacts: {artifact_summary}"
            )
        except Exception as e:
            logger.error("Failed to retrieve results for job %s: %s", job.id, e)
            job.result_summary = f"Pipeline completed but result retrieval failed: {e}"

        # Notify the deliberation via callback
        if self._result_callback and job.session_id:
            try:
                await self._result_callback(job.session_id, job)
            except Exception as e:
                logger.error("Result callback failed for job %s: %s", job.id, e)

    # ---- Accessors for proposals ----

    def get_proposal(self, proposal_id: UUID) -> Optional[ActionProposal]:
        """Get a proposal by ID."""
        return self._proposals.get(proposal_id)

    def list_pending_proposals(self, session_id: UUID) -> List[ActionProposal]:
        """List pending proposals for a session."""
        return [
            p
            for p in self._proposals.values()
            if p.session_id == session_id and p.status == ActionProposalStatus.PENDING
        ]
