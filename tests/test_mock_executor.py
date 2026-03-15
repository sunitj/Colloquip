"""Tests for mock Nextflow executor."""

from colloquip.jobs.executor import MockNextflowExecutor
from colloquip.models import JobStatus


class TestMockNextflowExecutor:
    async def test_submit_returns_run_id(self):
        executor = MockNextflowExecutor()
        run_id = await executor.submit(
            script_path="main.nf",
            profile="standard",
            work_dir="./work",
        )
        assert run_id.startswith("mock-")
        assert len(run_id) > 5

    async def test_poll_transitions_to_completed(self):
        executor = MockNextflowExecutor(complete_after_polls=2)
        run_id = await executor.submit("main.nf", "standard", "./work")

        # First poll: still running
        status, msg = await executor.poll_status(run_id)
        assert status == JobStatus.RUNNING
        assert "poll 1" in msg

        # Second poll: completed
        status, msg = await executor.poll_status(run_id)
        assert status == JobStatus.COMPLETED

    async def test_poll_unknown_run_id(self):
        executor = MockNextflowExecutor()
        status, msg = await executor.poll_status("nonexistent")
        assert status == JobStatus.FAILED
        assert "Unknown" in msg

    async def test_get_results_returns_artifacts(self):
        executor = MockNextflowExecutor()
        run_id = await executor.submit("main.nf", "standard", "./work")
        artifacts = await executor.get_results(run_id, "./work")
        assert len(artifacts) == 3
        types = {a.artifact_type for a in artifacts}
        assert "pdb" in types
        assert "csv" in types
        assert "a3m" in types

    async def test_cancel(self):
        executor = MockNextflowExecutor()
        run_id = await executor.submit("main.nf", "standard", "./work")
        assert await executor.cancel(run_id) is True
        # Verify the internal status was set to cancelled
        assert executor._jobs[run_id]["status"] == JobStatus.CANCELLED

    async def test_cancel_unknown(self):
        executor = MockNextflowExecutor()
        assert await executor.cancel("nonexistent") is False

    async def test_submit_with_params(self):
        executor = MockNextflowExecutor()
        run_id = await executor.submit(
            script_path="main.nf",
            profile="aws_batch",
            work_dir="./work",
            params={"input": "test.fasta", "model": "monomer"},
        )
        assert run_id.startswith("mock-")
        job_data = executor._jobs[run_id]
        assert job_data["profile"] == "aws_batch"
        assert job_data["params"]["input"] == "test.fasta"
