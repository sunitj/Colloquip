"""Nextflow process library and job status tools.

Provides agents with tools to browse available Nextflow processes and
check the status of running/completed jobs.
"""

import logging
from typing import Any, Dict, List, Optional

from colloquip.tools.interface import BaseSearchTool, SearchResult, ToolResult

logger = logging.getLogger(__name__)


class NextflowProcessLibraryTool(BaseSearchTool):
    """Tool for browsing the Nextflow process library.

    Allows agents to discover available computational processes for pipeline
    composition, including their input/output channels and parameters.
    """

    _name = "nf_process_library"
    _description = (
        "Browse the Nextflow process library to find available computational "
        "processes for pipeline building. Search by category (e.g., "
        "'structure_prediction', 'sequence_alignment', 'protein_design') "
        "or by keyword."
    )

    def __init__(self, process_catalog: Optional[List[Dict]] = None, **kwargs):
        self._catalog = process_catalog or []

    def set_catalog(self, catalog: List[Dict]):
        """Set the process catalog (list of NextflowProcess dicts)."""
        self._catalog = catalog

    @property
    def tool_schema(self) -> Dict[str, Any]:
        return {
            "name": self._name,
            "description": self._description,
            "input_schema": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": (
                            "Filter by category: structure_prediction, "
                            "sequence_alignment, protein_design, simulation, "
                            "structure_search, structure_refinement, analysis."
                        ),
                    },
                    "query": {
                        "type": "string",
                        "description": "Keyword search within process names and descriptions.",
                    },
                },
            },
        }

    async def execute(self, **kwargs) -> ToolResult:
        category = kwargs.get("category", "")
        query = kwargs.get("query", "").lower()

        filtered = self._catalog
        if category:
            filtered = [p for p in filtered if p.get("category", "") == category]
        if query:
            filtered = [
                p
                for p in filtered
                if query in p.get("name", "").lower()
                or query in p.get("description", "").lower()
                or query in p.get("process_id", "").lower()
            ]

        results = []
        for proc in filtered:
            inputs = ", ".join(
                f"{ch['name']} ({ch['data_type']})" for ch in proc.get("input_channels", [])
            )
            outputs = ", ".join(
                f"{ch['name']} ({ch['data_type']})" for ch in proc.get("output_channels", [])
            )
            params = ", ".join(p.get("name", "") for p in proc.get("parameters", []))
            res = proc.get("resource_requirements", {})
            resources = (
                f"CPUs: {res.get('cpus', 1)}, "
                f"Memory: {res.get('memory_gb', 4)}GB, "
                f"GPU: {res.get('gpu', False)}, "
                f"Est. runtime: {res.get('estimated_runtime_minutes', 30)}min"
            )

            abstract = (
                f"{proc.get('description', '')}\n"
                f"Category: {proc.get('category', '')}\n"
                f"Inputs: {inputs}\n"
                f"Outputs: {outputs}\n"
                f"Parameters: {params}\n"
                f"Resources: {resources}\n"
                f"Container: {proc.get('container', '')}\n"
                f"Version: {proc.get('version', '')}"
            )

            results.append(
                SearchResult(
                    title=f"{proc.get('process_id', '')} - {proc.get('name', '')}",
                    abstract=abstract,
                    source_type="nf_process",
                    source_id=proc.get("process_id", ""),
                )
            )

        return ToolResult(
            source="nf_process_library",
            query=f"category={category} query={query}".strip(),
            results=results,
            execution_time_ms=0.1,
        )


class JobStatusTool(BaseSearchTool):
    """Tool for checking computational job status.

    Allows agents to check the status and results of submitted jobs
    during deliberation.
    """

    _name = "job_status"
    _description = (
        "Check the status and results of a computational job. "
        "Use this to monitor running jobs or retrieve results "
        "from completed jobs."
    )

    def __init__(self, job_manager=None, **kwargs):
        self._job_manager = job_manager

    def set_job_manager(self, manager):
        """Set the job manager for status lookups."""
        self._job_manager = manager

    @property
    def tool_schema(self) -> Dict[str, Any]:
        return {
            "name": self._name,
            "description": self._description,
            "input_schema": {
                "type": "object",
                "properties": {
                    "job_id": {
                        "type": "string",
                        "description": "The UUID of the job to check.",
                    },
                    "session_id": {
                        "type": "string",
                        "description": (
                            "List all jobs for this session ID instead of checking a specific job."
                        ),
                    },
                },
            },
        }

    async def execute(self, **kwargs) -> ToolResult:
        job_id = kwargs.get("job_id", "")
        session_id = kwargs.get("session_id", "")

        if not self._job_manager:
            return ToolResult(
                source="job_status",
                query=job_id or session_id,
                error="Job manager not configured.",
            )

        if job_id:
            from uuid import UUID

            job = await self._job_manager.get_job(UUID(job_id))
            if not job:
                return ToolResult(
                    source="job_status",
                    query=job_id,
                    error=f"Job {job_id} not found.",
                )

            result_info = f"Status: {job.status.value}"
            if job.result_summary:
                result_info += f"\nSummary: {job.result_summary}"
            if job.result_artifacts:
                artifacts = ", ".join(f"{a.name} ({a.artifact_type})" for a in job.result_artifacts)
                result_info += f"\nArtifacts: {artifacts}"
            if job.error_message:
                result_info += f"\nError: {job.error_message}"

            return ToolResult(
                source="job_status",
                query=job_id,
                results=[
                    SearchResult(
                        title=f"Job {job_id[:8]}... - {job.status.value}",
                        abstract=result_info,
                        source_type="job",
                        source_id=str(job.id),
                    )
                ],
            )

        if session_id:
            from uuid import UUID

            jobs = await self._job_manager.list_jobs(UUID(session_id))
            results = []
            for job in jobs:
                results.append(
                    SearchResult(
                        title=f"Job {str(job.id)[:8]}... - {job.status.value}",
                        abstract=(
                            f"Pipeline: {job.pipeline.name}\n"
                            f"Status: {job.status.value}\n"
                            f"Agent: {job.agent_id}"
                        ),
                        source_type="job",
                        source_id=str(job.id),
                    )
                )
            return ToolResult(
                source="job_status",
                query=session_id,
                results=results,
            )

        return ToolResult(
            source="job_status",
            query="",
            error="Provide either job_id or session_id.",
        )


class MockJobStatusTool(BaseSearchTool):
    """Mock job status tool for testing."""

    _name = "job_status"
    _description = "Check the status and results of a computational job."

    @property
    def tool_schema(self) -> Dict[str, Any]:
        return {
            "name": self._name,
            "description": self._description,
            "input_schema": {
                "type": "object",
                "properties": {
                    "job_id": {"type": "string", "description": "Job UUID."},
                    "session_id": {"type": "string", "description": "Session UUID."},
                },
            },
        }

    async def execute(self, **kwargs) -> ToolResult:
        job_id = kwargs.get("job_id", "mock-job-001")
        return ToolResult(
            source="job_status",
            query=job_id,
            results=[
                SearchResult(
                    title=f"Job {job_id[:8]}... - completed",
                    abstract=(
                        "Status: completed\n"
                        "Pipeline: alphafold2_structure_prediction\n"
                        "Summary: Structure predicted with pLDDT 87.3, "
                        "high confidence in core domain.\n"
                        "Artifacts: structure.pdb (pdb), scores.csv (csv)"
                    ),
                    source_type="job",
                    source_id=job_id,
                )
            ],
            execution_time_ms=0.1,
        )
