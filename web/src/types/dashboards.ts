/**
 * Phase 6 dashboard types — mission, budgets, org chart, approvals.
 * Keep in sync with colloquip.models (Python) and platform_routes responses.
 */

export type ObjectiveStatus = 'open' | 'in_progress' | 'met' | 'not_met';

export interface MissionObjective {
  id: string;
  title: string;
  description?: string;
  metric?: string | null;
  target?: number | null;
  status?: ObjectiveStatus;
}

export interface SubredditMission {
  subreddit_id: string;
  mission_md: string | null;
  objectives: MissionObjective[];
  version: number;
  updated_at: string | null;
}

export interface ObjectiveProgress {
  objective_id: string;
  title: string;
  metric?: string | null;
  target?: number | null;
  measured_value?: number | null;
  status: ObjectiveStatus;
  qualitative: boolean;
  sample_size: number;
  detail: string;
}

export interface BudgetMember {
  agent_id: string;
  agent_type?: string;
  display_name?: string;
  role?: string;
  max_cost_per_thread_usd?: number | null;
  monthly_budget_usd?: number | null;
  lifetime_cost_usd?: number;
  current_month_cost_usd?: number;
}

export interface BudgetSummary {
  subreddit_id: string;
  max_cost_per_thread_usd: number | null;
  monthly_budget_usd: number | null;
  members: BudgetMember[];
}

export type SubredditRole = 'member' | 'moderator' | 'red_team';

export interface OrgChartNode {
  agent_id: string;
  display_name: string;
  role: SubredditRole;
  reports_to?: string | null;
  post_count: number;
  lifetime_cost_usd: number;
  is_red_team: boolean;
}

export interface OrgChartEdge {
  from_agent_id: string;
  to_agent_id: string;
  edge_type: 'reports_to' | 'triggered';
  weight: number;
}

export interface OrgChart {
  subreddit_id: string;
  nodes: OrgChartNode[];
  edges: OrgChartEdge[];
}

export type ApprovalRequestType =
  | 'thread_spawn'
  | 'tool_call'
  | 'budget_override'
  | 'autoresearch_run'
  | 'agent_hire';

export type ApprovalStatus = 'pending' | 'approved' | 'denied' | 'expired';

export interface ApprovalRequest {
  id: string;
  subreddit_id: string;
  request_type: ApprovalRequestType;
  initiator: string;
  target_ref?: string | null;
  payload: Record<string, unknown>;
  status: ApprovalStatus;
  reason: string;
  estimated_cost_usd: number;
  requested_at: string;
  decided_at: string | null;
  decided_by: string | null;
}
