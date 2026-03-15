/** TypeScript types for the jobs/pipelines subsystem */

export type JobStatus =
  | 'pending'
  | 'approved'
  | 'submitted'
  | 'running'
  | 'completed'
  | 'failed'
  | 'cancelled';

export type ComputeBackend = 'local' | 'aws_batch' | 'spark';

export type ActionProposalStatus = 'pending' | 'approved' | 'rejected' | 'expired';

export interface ChannelSpec {
  name: string;
  data_type: string;
  description: string;
  optional: boolean;
}

export interface ParamSpec {
  name: string;
  param_type: string;
  description: string;
  default?: unknown;
  required: boolean;
}

export interface ResourceSpec {
  cpus: number;
  memory_gb: number;
  gpu: boolean;
  estimated_runtime_minutes: number;
}

export interface NextflowProcess {
  process_id: string;
  name: string;
  description: string;
  category: string;
  input_channels: ChannelSpec[];
  output_channels: ChannelSpec[];
  parameters: ParamSpec[];
  container: string;
  resource_requirements: ResourceSpec;
  version: string;
}

export interface PipelineStep {
  process_id: string;
  step_name: string;
  input_mappings: Record<string, string>;
  parameter_overrides: Record<string, unknown>;
}

export interface PipelineDefinition {
  id: string;
  name: string;
  description: string;
  steps: PipelineStep[];
  parameters: Record<string, unknown>;
}

export interface JobArtifact {
  name: string;
  artifact_type: string;
  path: string;
  size_bytes: number;
  description: string;
}

export interface Job {
  id: string;
  session_id: string;
  thread_id?: string;
  agent_id: string;
  pipeline: PipelineDefinition;
  compute_backend: ComputeBackend;
  compute_profile: string;
  status: JobStatus;
  nextflow_run_id?: string;
  result_summary?: string;
  result_artifacts: JobArtifact[];
  error_message?: string;
  submitted_at?: string;
  completed_at?: string;
  created_at: string;
}

export interface ActionProposal {
  id: string;
  session_id: string;
  thread_id?: string;
  agent_id: string;
  action_type: string;
  description: string;
  rationale: string;
  proposed_pipeline?: PipelineDefinition;
  proposed_params: Record<string, unknown>;
  status: ActionProposalStatus;
  reviewed_by?: string;
  review_note?: string;
  created_at: string;
  reviewed_at?: string;
}

export interface DataConnection {
  id: string;
  subreddit_id: string;
  name: string;
  description: string;
  db_type: string;
  read_only: boolean;
  enabled: boolean;
}
