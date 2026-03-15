"""Pipeline builder: compose and validate Nextflow pipelines from process library.

Validates channel compatibility between steps and generates Nextflow DSL2
workflow scripts.
"""

import logging
from typing import Dict, List, Optional, Tuple
from uuid import uuid4

from colloquip.models import (
    ChannelSpec,
    NextflowProcess,
    PipelineDefinition,
    PipelineStep,
)

logger = logging.getLogger(__name__)


class PipelineValidationError(Exception):
    """Raised when pipeline validation fails."""


class PipelineBuilder:
    """Builds and validates Nextflow pipelines from library processes.

    Validates channel compatibility between steps and generates
    Nextflow DSL2 workflow scripts.
    """

    def __init__(self, process_catalog: Optional[Dict[str, NextflowProcess]] = None):
        self._catalog: Dict[str, NextflowProcess] = process_catalog or {}

    def set_catalog(self, processes: List[NextflowProcess]):
        """Set the process catalog from a list of processes."""
        self._catalog = {p.process_id: p for p in processes}

    def get_process(self, process_id: str) -> Optional[NextflowProcess]:
        """Look up a process by ID."""
        return self._catalog.get(process_id)

    def validate_pipeline(self, pipeline: PipelineDefinition) -> List[str]:
        """Validate a pipeline definition.

        Returns a list of error messages. Empty list means valid.
        """
        errors: List[str] = []

        if not pipeline.steps:
            errors.append("Pipeline has no steps")
            return errors

        # Track available outputs from previous steps
        available_outputs: Dict[str, ChannelSpec] = {}

        for i, step in enumerate(pipeline.steps):
            process = self._catalog.get(step.process_id)
            if not process:
                errors.append(f"Step {i} ({step.step_name}): Unknown process '{step.process_id}'")
                continue

            # Validate required inputs are mapped
            for input_ch in process.input_channels:
                if input_ch.optional:
                    continue
                if input_ch.name not in step.input_mappings:
                    # Check if it's the first step and input comes from pipeline params
                    if i == 0:
                        if input_ch.name not in pipeline.parameters:
                            errors.append(
                                f"Step {i} ({step.step_name}): Required input "
                                f"'{input_ch.name}' not mapped and not in pipeline parameters"
                            )
                    else:
                        errors.append(
                            f"Step {i} ({step.step_name}): Required input "
                            f"'{input_ch.name}' not mapped"
                        )

            # Validate input mappings point to valid sources
            for input_name, source in step.input_mappings.items():
                # Source format: "step_name.output_name" or "params.param_name"
                if source.startswith("params."):
                    param_name = source[7:]
                    if param_name not in pipeline.parameters:
                        errors.append(
                            f"Step {i} ({step.step_name}): Input '{input_name}' "
                            f"references missing parameter '{param_name}'"
                        )
                elif "." in source:
                    src_step, src_output = source.split(".", 1)
                    output_key = f"{src_step}.{src_output}"
                    if output_key not in available_outputs:
                        errors.append(
                            f"Step {i} ({step.step_name}): Input '{input_name}' "
                            f"references unavailable output '{source}'"
                        )
                    else:
                        # Check type compatibility
                        src_spec = available_outputs[output_key]
                        input_spec = next(
                            (ch for ch in process.input_channels if ch.name == input_name),
                            None,
                        )
                        if input_spec and src_spec.data_type != input_spec.data_type:
                            errors.append(
                                f"Step {i} ({step.step_name}): Type mismatch for "
                                f"'{input_name}': expected '{input_spec.data_type}', "
                                f"got '{src_spec.data_type}' from {source}"
                            )

            # Validate parameter overrides
            valid_params = {p.name for p in process.parameters}
            for param_name in step.parameter_overrides:
                if param_name not in valid_params:
                    errors.append(f"Step {i} ({step.step_name}): Unknown parameter '{param_name}'")

            # Register this step's outputs as available
            for output_ch in process.output_channels:
                output_key = f"{step.step_name}.{output_ch.name}"
                available_outputs[output_key] = output_ch

        return errors

    def build_pipeline(
        self,
        name: str,
        steps: List[Dict],
        parameters: Optional[Dict] = None,
        description: str = "",
    ) -> Tuple[PipelineDefinition, List[str]]:
        """Build a pipeline from step definitions.

        Args:
            name: Pipeline name
            steps: List of step dicts with process_id, step_name,
                   input_mappings, and parameter_overrides
            parameters: Pipeline-level parameters
            description: Pipeline description

        Returns:
            Tuple of (PipelineDefinition, list of validation errors)
        """
        pipeline_steps = [PipelineStep(**s) for s in steps]
        pipeline = PipelineDefinition(
            id=uuid4(),
            name=name,
            description=description,
            steps=pipeline_steps,
            parameters=parameters or {},
        )
        errors = self.validate_pipeline(pipeline)
        return pipeline, errors

    def generate_nextflow_script(self, pipeline: PipelineDefinition) -> str:
        """Generate a Nextflow DSL2 workflow script from a pipeline definition.

        Returns the script content as a string.
        """
        lines = [
            "#!/usr/bin/env nextflow",
            "nextflow.enable.dsl=2",
            "",
            f"// Pipeline: {pipeline.name}",
            f"// Description: {pipeline.description}",
            f"// Generated pipeline ID: {pipeline.id}",
            "",
        ]

        # Add parameter declarations
        if pipeline.parameters:
            lines.append("// Pipeline parameters")
            for name, value in pipeline.parameters.items():
                if isinstance(value, str):
                    lines.append(f"params.{name} = '{value}'")
                else:
                    lines.append(f"params.{name} = {value}")
            lines.append("")

        # Include process definitions
        included_processes = set()
        for step in pipeline.steps:
            if step.process_id not in included_processes:
                process = self._catalog.get(step.process_id)
                if process:
                    lines.append(
                        f"include {{ {step.process_id} }} from './modules/{step.process_id}'"
                    )
                    included_processes.add(step.process_id)
        lines.append("")

        # Build workflow block
        lines.append("workflow {")

        for i, step in enumerate(pipeline.steps):
            process = self._catalog.get(step.process_id)
            if not process:
                continue

            # Build input channel references
            inputs = []
            for input_ch in process.input_channels:
                if input_ch.name in step.input_mappings:
                    source = step.input_mappings[input_ch.name]
                    if source.startswith("params."):
                        inputs.append(f"Channel.fromPath(params.{source[7:]})")
                    elif "." in source:
                        src_step, src_output = source.split(".", 1)
                        inputs.append(f"{src_step}.out.{src_output}")
                    else:
                        inputs.append(source)
                elif input_ch.name in pipeline.parameters:
                    inputs.append(f"Channel.fromPath(params.{input_ch.name})")

            input_str = ", ".join(inputs) if inputs else ""
            step_alias = step.step_name

            if step_alias != step.process_id:
                lines.append(f"    {step_alias} = {step.process_id}({input_str})")
            else:
                lines.append(f"    {step.process_id}({input_str})")

        lines.append("}")
        lines.append("")

        return "\n".join(lines)
