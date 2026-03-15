"""Tests for Nextflow process library and job status tools."""

from uuid import uuid4

# =========================================================================
# Process Library Tool
# =========================================================================

_SAMPLE_CATALOG = [
    {
        "process_id": "alphafold2",
        "name": "AlphaFold2 Structure Prediction",
        "description": "Predict protein structure using AlphaFold2",
        "category": "structure_prediction",
        "input_channels": [
            {"name": "fasta", "data_type": "fasta", "description": "Input sequence"}
        ],
        "output_channels": [
            {"name": "structure", "data_type": "pdb", "description": "Predicted structure"}
        ],
        "parameters": [{"name": "model_preset", "param_type": "string"}],
        "resource_requirements": {
            "cpus": 8,
            "memory_gb": 32,
            "gpu": True,
            "estimated_runtime_minutes": 60,
        },
        "container": "nfcore/alphafold:2.3.0",
        "version": "2.3.0",
    },
    {
        "process_id": "mmseqs2_search",
        "name": "MMseqs2 Sequence Search",
        "description": "Fast sequence search with MMseqs2",
        "category": "sequence_alignment",
        "input_channels": [
            {"name": "fasta", "data_type": "fasta", "description": "Query sequences"}
        ],
        "output_channels": [
            {"name": "alignments", "data_type": "a3m", "description": "Alignment results"}
        ],
        "parameters": [{"name": "sensitivity", "param_type": "float"}],
        "resource_requirements": {
            "cpus": 4,
            "memory_gb": 16,
            "gpu": False,
            "estimated_runtime_minutes": 15,
        },
        "container": "soedinglab/mmseqs2:15",
        "version": "15.0",
    },
]


class TestNextflowProcessLibraryTool:
    async def test_list_all(self):
        from colloquip.tools.nextflow_tool import NextflowProcessLibraryTool

        tool = NextflowProcessLibraryTool(process_catalog=_SAMPLE_CATALOG)
        result = await tool.execute()
        assert result.error is None
        assert len(result.results) == 2

    async def test_filter_by_category(self):
        from colloquip.tools.nextflow_tool import NextflowProcessLibraryTool

        tool = NextflowProcessLibraryTool(process_catalog=_SAMPLE_CATALOG)
        result = await tool.execute(category="structure_prediction")
        assert len(result.results) == 1
        assert "alphafold2" in result.results[0].source_id

    async def test_filter_by_keyword(self):
        from colloquip.tools.nextflow_tool import NextflowProcessLibraryTool

        tool = NextflowProcessLibraryTool(process_catalog=_SAMPLE_CATALOG)
        result = await tool.execute(query="mmseqs")
        assert len(result.results) == 1
        assert "mmseqs2" in result.results[0].source_id

    async def test_no_matches(self):
        from colloquip.tools.nextflow_tool import NextflowProcessLibraryTool

        tool = NextflowProcessLibraryTool(process_catalog=_SAMPLE_CATALOG)
        result = await tool.execute(category="nonexistent")
        assert len(result.results) == 0

    async def test_empty_catalog(self):
        from colloquip.tools.nextflow_tool import NextflowProcessLibraryTool

        tool = NextflowProcessLibraryTool()
        result = await tool.execute()
        assert len(result.results) == 0

    async def test_result_contains_details(self):
        from colloquip.tools.nextflow_tool import NextflowProcessLibraryTool

        tool = NextflowProcessLibraryTool(process_catalog=_SAMPLE_CATALOG)
        result = await tool.execute(category="structure_prediction")
        abstract = result.results[0].abstract
        assert "Inputs:" in abstract
        assert "Outputs:" in abstract
        assert "Resources:" in abstract
        assert "Container:" in abstract

    async def test_set_catalog(self):
        from colloquip.tools.nextflow_tool import NextflowProcessLibraryTool

        tool = NextflowProcessLibraryTool()
        assert len((await tool.execute()).results) == 0
        tool.set_catalog(_SAMPLE_CATALOG)
        assert len((await tool.execute()).results) == 2


# =========================================================================
# Job Status Tool
# =========================================================================


class TestJobStatusTool:
    async def test_no_manager_error(self):
        from colloquip.tools.nextflow_tool import JobStatusTool

        tool = JobStatusTool()
        result = await tool.execute(job_id=str(uuid4()))
        assert result.error is not None
        assert "not configured" in result.error

    async def test_no_params_error(self):
        from colloquip.tools.nextflow_tool import JobStatusTool

        tool = JobStatusTool()
        result = await tool.execute()
        assert result.error is not None


# =========================================================================
# Mock Job Status Tool
# =========================================================================


class TestMockJobStatusTool:
    async def test_returns_completed_job(self):
        from colloquip.tools.nextflow_tool import MockJobStatusTool

        tool = MockJobStatusTool()
        result = await tool.execute(job_id="test-job-001")
        assert result.error is None
        assert len(result.results) == 1
        assert "completed" in result.results[0].abstract.lower()
        assert "pdb" in result.results[0].abstract.lower()
