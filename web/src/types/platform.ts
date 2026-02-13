export type ThinkingType = 'assessment' | 'analysis' | 'review' | 'ideation';
export type ParticipationModel = 'observer' | 'guided' | 'participant' | 'approver';
export type ThreadStatus = 'active' | 'paused' | 'completed' | 'failed' | 'cancelled';
export type WatcherType = 'literature' | 'scheduled' | 'webhook';
export type TriageSignal = 'low' | 'medium' | 'high';
export type NotificationStatus = 'pending' | 'read' | 'acted' | 'dismissed';
export type AnnotationType = 'outdated' | 'correction' | 'confirmed' | 'context';

export interface Subreddit {
  id: string;
  name: string;
  display_name: string;
  description: string;
  thinking_type: ThinkingType;
  participation_model: ParticipationModel;
  member_count: number;
  thread_count: number;
  tool_ids: string[];
  has_red_team: boolean;
}

export interface SubredditDetail extends Subreddit {
  core_questions: string[];
  decision_context: string;
  primary_domain: string;
  members: AgentMember[];
  recruitment_gaps: RecruitmentGap[];
  max_cost_per_thread_usd: number;
}

export interface AgentMember {
  agent_id: string;
  agent_type: string;
  display_name: string;
  role: string;
  expertise_tags: string[];
  is_red_team: boolean;
  threads_participated: number;
  total_posts: number;
}

export interface RecruitmentGap {
  expertise: string;
  domain: string;
  is_red_team: boolean;
  has_curated_template: boolean;
}

export interface Agent {
  id: string;
  agent_type: string;
  display_name: string;
  expertise_tags: string[];
  is_red_team: boolean;
  subreddit_count: number;
}

export interface AgentDetail extends Agent {
  persona_prompt: string;
  phase_mandates: Record<string, string>;
  domain_keywords: string[];
  knowledge_scope: string;
  evaluation_criteria: string[];
  status: string;
  version: number;
}

export interface Thread {
  id: string;
  subreddit_id: string;
  subreddit_name: string;
  title: string;
  hypothesis: string;
  status: ThreadStatus;
  phase: string;
  post_count: number;
  estimated_cost_usd: number;
  created_at?: string;
}

export interface Memory {
  id: string;
  thread_id: string;
  subreddit_id: string;
  subreddit_name: string;
  topic: string;
  key_conclusions: string[];
  citations_used: string[];
  agents_involved: string[];
  template_type: string;
  confidence_level: string;
  evidence_quality: string;
  confidence: number;
  confidence_alpha: number;
  confidence_beta: number;
  created_at: string;
  annotations: MemoryAnnotation[];
}

export interface MemoryAnnotation {
  id: string;
  memory_id: string;
  annotation_type: AnnotationType;
  content: string;
  created_by: string;
  created_at: string;
}

export interface Notification {
  id: string;
  watcher_id: string;
  event_id: string;
  subreddit_id: string;
  title: string;
  summary: string;
  signal: TriageSignal;
  suggested_hypothesis: string | null;
  status: NotificationStatus;
  action_taken: string | null;
  thread_id: string | null;
  created_at: string;
  acted_at: string | null;
}

export interface Watcher {
  id: string;
  watcher_type: WatcherType;
  subreddit_id: string;
  name: string;
  description: string;
  query: string;
  poll_interval_seconds: number;
  enabled: boolean;
  created_at: string;
}

export interface CostSummary {
  thread_id: string;
  total_input_tokens: number;
  total_output_tokens: number;
  total_tokens: number;
  estimated_cost_usd: number;
  num_llm_calls: number;
  duration_seconds: number | null;
}

export interface CalibrationReport {
  agent_id: string;
  total_evaluations: number;
  correct: number;
  incorrect: number;
  partial: number;
  accuracy: number;
  domain_accuracy: Record<string, number>;
  systematic_biases: string[];
  is_meaningful: boolean;
}

export interface CalibrationOverview {
  total_outcomes: number;
  agents_with_data: number;
  agents_calibrated: number;
  agent_reports: CalibrationReport[];
}

export interface OutcomeReport {
  outcome_type: string;
  summary: string;
  evidence: string;
  conclusions_evaluated: Record<string, string>;
  agent_assessments: Record<string, string>;
  reported_by: string;
}
