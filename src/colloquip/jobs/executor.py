"""Nextflow executor: submit, monitor, and retrieve results from Nextflow runs.

Supports local execution and profile-based backend selection (AWS Batch, Spark).
"""

import asyncio
import logging
import os
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from colloquip.models import JobArtifact, JobStatus

logger = logging.getLogger(__name__)


class BaseExecutor(ABC):
    """Abstract base class for pipeline executors."""

    @abstractmethod
    async def submit(
        self,
        script_path: str,
        profile: str,
        work_dir: str,
        params: Optional[Dict[str, Any]] = None,
        config_path: Optional[str] = None,
    ) -> str:
        """Submit a pipeline for execution.

        Returns the run ID.
        """
        ...

    @abstractmethod
    async def poll_status(self, run_id: str) -> Tuple[JobStatus, Optional[str]]:
        """Check the status of a running pipeline.

        Returns (status, progress_message).
        """
        ...

    @abstractmethod
    async def get_results(self, run_id: str, work_dir: str) -> List[JobArtifact]:
        """Retrieve output artifacts from a completed run."""
        ...

    @abstractmethod
    async def cancel(self, run_id: str) -> bool:
        """Cancel a running pipeline. Returns True if cancelled."""
        ...


class NextflowExecutor(BaseExecutor):
    """Execute Nextflow pipelines via CLI subprocess.

    Uses Nextflow profiles for backend selection:
    - local: Run on the local machine
    - aws_batch: Submit to AWS Batch
    - spark: Submit to DGI Spark cluster
    """

    def __init__(
        self,
        nextflow_binary: str = "nextflow",
        default_config_path: Optional[str] = None,
    ):
        self.nextflow_binary = nextflow_binary
        self.default_config_path = default_config_path
        self._processes: Dict[str, asyncio.subprocess.Process] = {}

    async def submit(
        self,
        script_path: str,
        profile: str,
        work_dir: str,
        params: Optional[Dict[str, Any]] = None,
        config_path: Optional[str] = None,
    ) -> str:
        run_name = f"colloquip-{uuid.uuid4().hex[:12]}"
        cmd = [
            self.nextflow_binary,
            "run",
            script_path,
            "-name",
            run_name,
            "-profile",
            profile,
            "-work-dir",
            work_dir,
            "-with-report",
            os.path.join(work_dir, f"{run_name}-report.html"),
            "-with-trace",
            os.path.join(work_dir, f"{run_name}-trace.txt"),
        ]

        cfg = config_path or self.default_config_path
        if cfg:
            cmd.extend(["-c", cfg])

        if params:
            for key, value in params.items():
                cmd.extend([f"--{key}", str(value)])

        logger.info("Submitting Nextflow run: %s", " ".join(cmd))

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            self._processes[run_name] = process
            return run_name

        except FileNotFoundError:
            raise RuntimeError(
                f"Nextflow binary not found at '{self.nextflow_binary}'. "
                "Ensure Nextflow is installed and on the PATH."
            )

    async def poll_status(self, run_id: str) -> Tuple[JobStatus, Optional[str]]:
        process = self._processes.get(run_id)
        if not process:
            return JobStatus.FAILED, f"No process found for run {run_id}"

        if process.returncode is None:
            return JobStatus.RUNNING, "Pipeline is executing..."

        if process.returncode == 0:
            return JobStatus.COMPLETED, "Pipeline completed successfully"

        stderr = ""
        if process.stderr:
            data = await process.stderr.read()
            stderr = data.decode()[:500]
        return JobStatus.FAILED, f"Pipeline failed (exit code {process.returncode}): {stderr}"

    async def get_results(self, run_id: str, work_dir: str) -> List[JobArtifact]:
        artifacts = []
        work_path = Path(work_dir)

        # Check for standard output files
        report_path = work_path / f"{run_id}-report.html"
        if report_path.exists():
            artifacts.append(
                JobArtifact(
                    name=f"{run_id}-report.html",
                    artifact_type="html",
                    path=str(report_path),
                    size_bytes=report_path.stat().st_size,
                    description="Nextflow execution report",
                )
            )

        trace_path = work_path / f"{run_id}-trace.txt"
        if trace_path.exists():
            artifacts.append(
                JobArtifact(
                    name=f"{run_id}-trace.txt",
                    artifact_type="tsv",
                    path=str(trace_path),
                    size_bytes=trace_path.stat().st_size,
                    description="Nextflow execution trace",
                )
            )

        # Scan for output files in the results directory
        results_dir = work_path / "results"
        if results_dir.exists():
            for f in results_dir.rglob("*"):
                if f.is_file():
                    ext = f.suffix.lstrip(".")
                    artifacts.append(
                        JobArtifact(
                            name=f.name,
                            artifact_type=ext or "unknown",
                            path=str(f),
                            size_bytes=f.stat().st_size,
                            description=f"Output file: {f.relative_to(results_dir)}",
                        )
                    )

        return artifacts

    async def cancel(self, run_id: str) -> bool:
        process = self._processes.get(run_id)
        if not process:
            return False
        try:
            process.terminate()
            await asyncio.wait_for(process.wait(), timeout=10)
            return True
        except asyncio.TimeoutError:
            process.kill()
            return True


class MockNextflowExecutor(BaseExecutor):
    """Mock executor for testing without Nextflow installed.

    Simulates the submit → running → completed lifecycle.
    """

    def __init__(self, complete_after_polls: int = 2):
        self._jobs: Dict[str, Dict[str, Any]] = {}
        self._complete_after = complete_after_polls

    async def submit(
        self,
        script_path: str,
        profile: str,
        work_dir: str,
        params: Optional[Dict[str, Any]] = None,
        config_path: Optional[str] = None,
    ) -> str:
        run_id = f"mock-{uuid.uuid4().hex[:12]}"
        self._jobs[run_id] = {
            "status": JobStatus.RUNNING,
            "polls": 0,
            "script_path": script_path,
            "profile": profile,
            "work_dir": work_dir,
            "params": params or {},
            "submitted_at": datetime.now(timezone.utc),
        }
        logger.info("Mock submit: %s (profile=%s)", run_id, profile)
        return run_id

    async def poll_status(self, run_id: str) -> Tuple[JobStatus, Optional[str]]:
        job = self._jobs.get(run_id)
        if not job:
            return JobStatus.FAILED, f"Unknown run {run_id}"

        job["polls"] += 1
        if job["polls"] >= self._complete_after:
            job["status"] = JobStatus.COMPLETED
            return JobStatus.COMPLETED, "Mock pipeline completed successfully"

        return JobStatus.RUNNING, f"Mock pipeline running (poll {job['polls']})"

    async def get_results(self, run_id: str, work_dir: str) -> List[JobArtifact]:
        return [
            JobArtifact(
                name="predicted_structure.pdb",
                artifact_type="pdb",
                path=f"{work_dir}/results/predicted_structure.pdb",
                size_bytes=125000,
                description="Predicted protein structure",
            ),
            JobArtifact(
                name="confidence_scores.csv",
                artifact_type="csv",
                path=f"{work_dir}/results/confidence_scores.csv",
                size_bytes=4500,
                description="Per-residue confidence scores (pLDDT)",
            ),
            JobArtifact(
                name="alignment.a3m",
                artifact_type="a3m",
                path=f"{work_dir}/results/alignment.a3m",
                size_bytes=890000,
                description="Multiple sequence alignment",
            ),
        ]

    async def cancel(self, run_id: str) -> bool:
        if run_id in self._jobs:
            self._jobs[run_id]["status"] = JobStatus.CANCELLED
            return True
        return False
