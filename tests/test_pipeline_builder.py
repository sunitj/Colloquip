"""Tests for pipeline builder: validation, composition, and script generation."""

from uuid import uuid4

from colloquip.models import (
    ChannelSpec,
    NextflowProcess,
    ParamSpec,
    PipelineDefinition,
    PipelineStep,
    ResourceSpec,
)


def _make_process(
    process_id,
    input_channels=None,
    output_channels=None,
    parameters=None,
    category="test",
):
    return NextflowProcess(
        process_id=process_id,
        name=process_id.replace("_", " ").title(),
        description=f"Test process {process_id}",
        category=category,
        input_channels=input_channels or [],
        output_channels=output_channels or [],
        parameters=parameters or [],
        container=f"test/{process_id}:latest",
        resource_requirements=ResourceSpec(),
    )


# Two processes that chain: fasta → structure
_PROC_FOLD = _make_process(
    "fold",
    input_channels=[ChannelSpec(name="fasta", data_type="fasta", description="Input")],
    output_channels=[ChannelSpec(name="structure", data_type="pdb", description="Output")],
    parameters=[ParamSpec(name="model", param_type="string", description="Model to use")],
)

_PROC_RELAX = _make_process(
    "relax",
    input_channels=[ChannelSpec(name="structure", data_type="pdb", description="Input PDB")],
    output_channels=[ChannelSpec(name="relaxed", data_type="pdb", description="Relaxed PDB")],
)

_PROC_ANALYSIS = _make_process(
    "analysis",
    input_channels=[ChannelSpec(name="data", data_type="csv", description="Input CSV")],
    output_channels=[ChannelSpec(name="report", data_type="html", description="Report")],
)


def _make_catalog():
    from colloquip.jobs.pipeline_builder import PipelineBuilder

    return PipelineBuilder(
        process_catalog={
            "fold": _PROC_FOLD,
            "relax": _PROC_RELAX,
            "analysis": _PROC_ANALYSIS,
        }
    )


# =========================================================================
# Pipeline Validation
# =========================================================================


class TestPipelineValidation:
    def test_empty_steps(self):
        builder = _make_catalog()
        pipeline = PipelineDefinition(id=uuid4(), name="empty", steps=[], parameters={})
        errors = builder.validate_pipeline(pipeline)
        assert len(errors) == 1
        assert "no steps" in errors[0].lower()

    def test_unknown_process(self):
        builder = _make_catalog()
        pipeline = PipelineDefinition(
            id=uuid4(),
            name="bad",
            steps=[PipelineStep(process_id="nonexistent", step_name="s1")],
            parameters={},
        )
        errors = builder.validate_pipeline(pipeline)
        assert any("Unknown process" in e for e in errors)

    def test_missing_required_input_first_step(self):
        builder = _make_catalog()
        pipeline = PipelineDefinition(
            id=uuid4(),
            name="missing",
            steps=[
                PipelineStep(process_id="fold", step_name="fold1", input_mappings={}),
            ],
            parameters={},
        )
        errors = builder.validate_pipeline(pipeline)
        assert any("fasta" in e and "not mapped" in e for e in errors)

    def test_first_step_with_pipeline_param(self):
        builder = _make_catalog()
        pipeline = PipelineDefinition(
            id=uuid4(),
            name="ok",
            steps=[
                PipelineStep(process_id="fold", step_name="fold1", input_mappings={}),
            ],
            parameters={"fasta": "/path/to/input.fasta"},
        )
        errors = builder.validate_pipeline(pipeline)
        assert len(errors) == 0

    def test_missing_required_input_later_step(self):
        builder = _make_catalog()
        pipeline = PipelineDefinition(
            id=uuid4(),
            name="bad_chain",
            steps=[
                PipelineStep(
                    process_id="fold",
                    step_name="fold1",
                    input_mappings={"fasta": "params.fasta"},
                ),
                PipelineStep(
                    process_id="relax",
                    step_name="relax1",
                    input_mappings={},  # Missing structure mapping
                ),
            ],
            parameters={"fasta": "/input.fasta"},
        )
        errors = builder.validate_pipeline(pipeline)
        assert any("structure" in e and "not mapped" in e for e in errors)

    def test_type_mismatch(self):
        builder = _make_catalog()
        pipeline = PipelineDefinition(
            id=uuid4(),
            name="mismatch",
            steps=[
                PipelineStep(
                    process_id="fold",
                    step_name="fold1",
                    input_mappings={"fasta": "params.fasta"},
                ),
                PipelineStep(
                    process_id="analysis",
                    step_name="analyze",
                    input_mappings={"data": "fold1.structure"},  # pdb != csv
                ),
            ],
            parameters={"fasta": "/input.fasta"},
        )
        errors = builder.validate_pipeline(pipeline)
        assert any("Type mismatch" in e for e in errors)

    def test_valid_two_step_chain(self):
        builder = _make_catalog()
        pipeline = PipelineDefinition(
            id=uuid4(),
            name="fold_relax",
            steps=[
                PipelineStep(
                    process_id="fold",
                    step_name="fold1",
                    input_mappings={"fasta": "params.fasta"},
                ),
                PipelineStep(
                    process_id="relax",
                    step_name="relax1",
                    input_mappings={"structure": "fold1.structure"},
                ),
            ],
            parameters={"fasta": "/input.fasta"},
        )
        errors = builder.validate_pipeline(pipeline)
        assert errors == []

    def test_invalid_parameter_override(self):
        builder = _make_catalog()
        pipeline = PipelineDefinition(
            id=uuid4(),
            name="bad_param",
            steps=[
                PipelineStep(
                    process_id="fold",
                    step_name="fold1",
                    input_mappings={"fasta": "params.fasta"},
                    parameter_overrides={"nonexistent_param": "value"},
                ),
            ],
            parameters={"fasta": "/input.fasta"},
        )
        errors = builder.validate_pipeline(pipeline)
        assert any("Unknown parameter" in e for e in errors)

    def test_reference_missing_param(self):
        builder = _make_catalog()
        pipeline = PipelineDefinition(
            id=uuid4(),
            name="bad_ref",
            steps=[
                PipelineStep(
                    process_id="fold",
                    step_name="fold1",
                    input_mappings={"fasta": "params.missing_param"},
                ),
            ],
            parameters={},
        )
        errors = builder.validate_pipeline(pipeline)
        assert any("missing parameter" in e for e in errors)

    def test_reference_unavailable_output(self):
        builder = _make_catalog()
        pipeline = PipelineDefinition(
            id=uuid4(),
            name="bad_ref",
            steps=[
                PipelineStep(
                    process_id="fold",
                    step_name="fold1",
                    input_mappings={"fasta": "params.fasta"},
                ),
                PipelineStep(
                    process_id="relax",
                    step_name="relax1",
                    input_mappings={"structure": "nonexistent_step.output"},
                ),
            ],
            parameters={"fasta": "/input.fasta"},
        )
        errors = builder.validate_pipeline(pipeline)
        assert any("unavailable output" in e for e in errors)


# =========================================================================
# Build Pipeline
# =========================================================================


class TestBuildPipeline:
    def test_build_valid(self):
        builder = _make_catalog()
        pipeline, errors = builder.build_pipeline(
            name="test_pipeline",
            steps=[
                {
                    "process_id": "fold",
                    "step_name": "fold1",
                    "input_mappings": {"fasta": "params.fasta"},
                },
            ],
            parameters={"fasta": "/input.fasta"},
        )
        assert errors == []
        assert pipeline.name == "test_pipeline"
        assert len(pipeline.steps) == 1
        assert pipeline.id is not None

    def test_build_with_errors(self):
        builder = _make_catalog()
        pipeline, errors = builder.build_pipeline(
            name="bad",
            steps=[{"process_id": "nonexistent", "step_name": "s1"}],
        )
        assert len(errors) > 0

    def test_get_process(self):
        builder = _make_catalog()
        assert builder.get_process("fold") is not None
        assert builder.get_process("nonexistent") is None

    def test_set_catalog(self):
        from colloquip.jobs.pipeline_builder import PipelineBuilder

        builder = PipelineBuilder()
        assert builder.get_process("fold") is None
        builder.set_catalog([_PROC_FOLD, _PROC_RELAX])
        assert builder.get_process("fold") is not None


# =========================================================================
# Script Generation
# =========================================================================


class TestGenerateNextflowScript:
    def test_generates_dsl2_header(self):
        builder = _make_catalog()
        pipeline = PipelineDefinition(
            id=uuid4(),
            name="test",
            description="A test pipeline",
            steps=[
                PipelineStep(
                    process_id="fold",
                    step_name="fold1",
                    input_mappings={"fasta": "params.fasta"},
                ),
            ],
            parameters={"fasta": "/input.fasta"},
        )
        script = builder.generate_nextflow_script(pipeline)
        assert "nextflow.enable.dsl=2" in script
        assert "Pipeline: test" in script

    def test_includes_processes(self):
        builder = _make_catalog()
        pipeline = PipelineDefinition(
            id=uuid4(),
            name="chain",
            steps=[
                PipelineStep(
                    process_id="fold",
                    step_name="fold1",
                    input_mappings={"fasta": "params.fasta"},
                ),
                PipelineStep(
                    process_id="relax",
                    step_name="relax1",
                    input_mappings={"structure": "fold1.structure"},
                ),
            ],
            parameters={"fasta": "/input.fasta"},
        )
        script = builder.generate_nextflow_script(pipeline)
        assert "include { fold }" in script
        assert "include { relax }" in script

    def test_workflow_block(self):
        builder = _make_catalog()
        pipeline = PipelineDefinition(
            id=uuid4(),
            name="test",
            steps=[
                PipelineStep(
                    process_id="fold",
                    step_name="fold1",
                    input_mappings={"fasta": "params.fasta"},
                ),
                PipelineStep(
                    process_id="relax",
                    step_name="relax1",
                    input_mappings={"structure": "fold1.structure"},
                ),
            ],
            parameters={"fasta": "/input.fasta"},
        )
        script = builder.generate_nextflow_script(pipeline)
        assert "workflow {" in script
        assert "fold1 = fold(Channel.fromPath(params.fasta))" in script
        assert "relax1 = relax(fold1.out.structure)" in script

    def test_parameter_declarations(self):
        builder = _make_catalog()
        pipeline = PipelineDefinition(
            id=uuid4(),
            name="test",
            steps=[
                PipelineStep(
                    process_id="fold",
                    step_name="fold1",
                    input_mappings={"fasta": "params.fasta"},
                ),
            ],
            parameters={"fasta": "/input.fasta", "num_models": 5},
        )
        script = builder.generate_nextflow_script(pipeline)
        assert "params.fasta = '/input.fasta'" in script
        assert "params.num_models = 5" in script
