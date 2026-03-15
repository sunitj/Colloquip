"""Tests for job manager: proposal lifecycle, job submission, monitoring."""

import tempfile
from uuid import uuid4

from colloquip.jobs.executor import MockNextflowExecutor
from colloquip.jobs.manager import JobManager
from colloquip.jobs.pipeline_builder import PipelineBuilder
from colloquip.models import (
    ActionProposalStatus,
    ChannelSpec,
    JobStatus,
    NextflowProcess,
    ParamSpec,
    PipelineDefinition,
    PipelineStep,
    ResourceSpec,
)


def _make_manager(auto_approve=False, max_concurrent=3, work_dir=None):
    proc = NextflowProcess(
        process_id="fold",
        name="Fold",
        description="Predict structure",
        category="structure_prediction",
        input_channels=[ChannelSpec(name="fasta", data_type="fasta", description="Input")],
        output_channels=[ChannelSpec(name="structure", data_type="pdb", description="Output")],
        parameters=[ParamSpec(name="model", param_type="string", description="Model")],
        container="test:latest",
        resource_requirements=ResourceSpec(),
    )
    builder = PipelineBuilder()
    builder.set_catalog([proc])
    executor = MockNextflowExecutor(complete_after_polls=1)
    return JobManager(
        executor=executor,
        pipeline_builder=builder,
        work_dir=work_dir or tempfile.mkdtemp(),
        poll_interval_seconds=1,
        max_concurrent_jobs=max_concurrent,
        auto_approve=auto_approve,
    )


def _make_pipeline():
    return PipelineDefinition(
        id=uuid4(),
        name="test_pipeline",
        description="Test",
        steps=[
            PipelineStep(
                process_id="fold",
                step_name="fold1",
                input_mappings={"fasta": "params.fasta"},
            ),
        ],
        parameters={"fasta": "/input.fasta"},
    )


# =========================================================================
# Proposals
# =========================================================================


class TestProposals:
    async def test_propose_job_creates_pending(self):
        mgr = _make_manager()
        pipeline = _make_pipeline()
        proposal = await mgr.propose_job(
            agent_id="bio_agent",
            session_id=uuid4(),
            pipeline=pipeline,
            rationale="Need structure prediction",
        )
        assert proposal.status == ActionProposalStatus.PENDING
        assert proposal.agent_id == "bio_agent"
        assert proposal.proposed_pipeline is not None

    async def test_auto_approve_submits_job(self):
        mgr = _make_manager(auto_approve=True)
        pipeline = _make_pipeline()
        session_id = uuid4()
        proposal = await mgr.propose_job(
            agent_id="bio_agent",
            session_id=session_id,
            pipeline=pipeline,
        )
        assert proposal.status == ActionProposalStatus.APPROVED
        # Job should be submitted
        jobs = await mgr.list_jobs(session_id)
        assert len(jobs) == 1
        assert jobs[0].status == JobStatus.SUBMITTED

    async def test_approve_proposal(self):
        mgr = _make_manager()
        pipeline = _make_pipeline()
        proposal = await mgr.propose_job(
            agent_id="bio_agent",
            session_id=uuid4(),
            pipeline=pipeline,
        )
        job = await mgr.approve_proposal(proposal.id, reviewer="admin", note="Looks good")
        assert job is not None
        assert job.status == JobStatus.SUBMITTED
        assert proposal.status == ActionProposalStatus.APPROVED
        assert proposal.reviewed_by == "admin"

    async def test_reject_proposal(self):
        mgr = _make_manager()
        pipeline = _make_pipeline()
        proposal = await mgr.propose_job(
            agent_id="bio_agent",
            session_id=uuid4(),
            pipeline=pipeline,
        )
        await mgr.reject_proposal(proposal.id, reviewer="admin", note="Not needed")
        assert proposal.status == ActionProposalStatus.REJECTED

    async def test_approve_nonexistent_returns_none(self):
        mgr = _make_manager()
        result = await mgr.approve_proposal(uuid4())
        assert result is None

    async def test_approve_already_approved_returns_none(self):
        mgr = _make_manager()
        pipeline = _make_pipeline()
        proposal = await mgr.propose_job(
            agent_id="bio_agent",
            session_id=uuid4(),
            pipeline=pipeline,
        )
        await mgr.approve_proposal(proposal.id)
        # Second approval should fail
        result = await mgr.approve_proposal(proposal.id)
        assert result is None

    async def test_list_pending_proposals(self):
        mgr = _make_manager()
        session_id = uuid4()
        pipeline = _make_pipeline()
        await mgr.propose_job(agent_id="a1", session_id=session_id, pipeline=pipeline)
        await mgr.propose_job(agent_id="a2", session_id=session_id, pipeline=pipeline)
        pending = mgr.list_pending_proposals(session_id)
        assert len(pending) == 2

    async def test_get_proposal(self):
        mgr = _make_manager()
        pipeline = _make_pipeline()
        proposal = await mgr.propose_job(
            agent_id="a1",
            session_id=uuid4(),
            pipeline=pipeline,
        )
        found = mgr.get_proposal(proposal.id)
        assert found is not None
        assert found.id == proposal.id


# =========================================================================
# Job Submission
# =========================================================================


class TestJobSubmission:
    async def test_submit_valid_pipeline(self):
        mgr = _make_manager()
        pipeline = _make_pipeline()
        job = await mgr.submit_job(
            session_id=uuid4(),
            agent_id="bio_agent",
            pipeline=pipeline,
        )
        assert job.status == JobStatus.SUBMITTED
        assert job.nextflow_run_id is not None

    async def test_submit_invalid_pipeline_fails(self):
        mgr = _make_manager()
        pipeline = PipelineDefinition(
            id=uuid4(),
            name="bad",
            steps=[PipelineStep(process_id="nonexistent", step_name="s1")],
            parameters={},
        )
        job = await mgr.submit_job(
            session_id=uuid4(),
            agent_id="bio_agent",
            pipeline=pipeline,
        )
        assert job.status == JobStatus.FAILED
        assert "validation failed" in job.error_message.lower()

    async def test_concurrent_job_limit(self):
        mgr = _make_manager(max_concurrent=1)
        pipeline = _make_pipeline()
        session_id = uuid4()

        # First job succeeds
        job1 = await mgr.submit_job(
            session_id=session_id,
            agent_id="a1",
            pipeline=pipeline,
        )
        assert job1.status == JobStatus.SUBMITTED

        # Second job should fail due to limit
        job2 = await mgr.submit_job(
            session_id=session_id,
            agent_id="a2",
            pipeline=pipeline,
        )
        assert job2.status == JobStatus.FAILED
        assert "Maximum concurrent" in job2.error_message

    async def test_get_job(self):
        mgr = _make_manager()
        pipeline = _make_pipeline()
        job = await mgr.submit_job(
            session_id=uuid4(),
            agent_id="a1",
            pipeline=pipeline,
        )
        found = await mgr.get_job(job.id)
        assert found is not None
        assert found.id == job.id

    async def test_list_jobs_by_session(self):
        mgr = _make_manager()
        pipeline = _make_pipeline()
        session_id = uuid4()
        await mgr.submit_job(session_id=session_id, agent_id="a1", pipeline=pipeline)
        await mgr.submit_job(session_id=session_id, agent_id="a2", pipeline=pipeline)
        jobs = await mgr.list_jobs(session_id)
        assert len(jobs) == 2


# =========================================================================
# Job Cancellation
# =========================================================================


class TestJobCancellation:
    async def test_cancel_submitted_job(self):
        mgr = _make_manager()
        pipeline = _make_pipeline()
        job = await mgr.submit_job(
            session_id=uuid4(),
            agent_id="a1",
            pipeline=pipeline,
        )
        result = await mgr.cancel_job(job.id)
        assert result is True
        assert job.status == JobStatus.CANCELLED

    async def test_cancel_nonexistent(self):
        mgr = _make_manager()
        result = await mgr.cancel_job(uuid4())
        assert result is False


# =========================================================================
# Monitoring
# =========================================================================


class TestJobMonitoring:
    async def test_poll_updates_status(self):
        mgr = _make_manager()
        pipeline = _make_pipeline()
        job = await mgr.submit_job(
            session_id=uuid4(),
            agent_id="a1",
            pipeline=pipeline,
        )
        assert job.status == JobStatus.SUBMITTED

        # Manually poll
        await mgr._poll_running_jobs()
        # MockNextflowExecutor with complete_after_polls=1 completes on first poll
        assert job.status == JobStatus.COMPLETED
        assert job.result_artifacts is not None
        assert len(job.result_artifacts) > 0

    async def test_result_callback_invoked(self):
        mgr = _make_manager()
        callback_calls = []

        async def mock_callback(session_id, job):
            callback_calls.append((session_id, job))

        mgr.set_result_callback(mock_callback)
        pipeline = _make_pipeline()
        session_id = uuid4()
        await mgr.submit_job(session_id=session_id, agent_id="a1", pipeline=pipeline)
        await mgr._poll_running_jobs()
        assert len(callback_calls) == 1
        assert callback_calls[0][0] == session_id

    async def test_start_stop_monitor(self):
        mgr = _make_manager()
        await mgr.start_monitor()
        assert mgr._running is True
        assert mgr._monitor_task is not None
        await mgr.stop_monitor()
        assert mgr._running is False
        assert mgr._monitor_task is None
