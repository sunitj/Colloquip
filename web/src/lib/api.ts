const API_BASE = '/api';

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    ...options,
  });
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(`API ${res.status}: ${text}`);
  }
  return res.json();
}

// Platform
export const platformInit = () => request<void>('/platform/init', { method: 'POST' });

// Subreddits
export const getSubreddits = () => request<import('@/types/platform').Subreddit[]>('/subreddits');
export const getSubreddit = (name: string) => request<import('@/types/platform').SubredditDetail>(`/subreddits/${name}`);
export const getSubredditMembers = (name: string) => request<{ members: import('@/types/platform').AgentMember[] }>(`/subreddits/${name}/members`);
export const getSubredditThreads = (name: string) => request<{ threads: import('@/types/platform').Thread[] }>(`/subreddits/${name}/threads`);
export const createSubreddit = (data: {
  name: string; display_name: string; description: string;
  thinking_type?: string; primary_domain?: string;
  required_expertise?: string[]; optional_expertise?: string[];
}) => request<import('@/types/platform').Subreddit>('/subreddits', { method: 'POST', body: JSON.stringify(data) });

// Threads
export const createThread = (subredditName: string, data: {
  title: string; hypothesis: string; mode?: string; max_turns?: number;
}) => request<import('@/types/platform').Thread>(`/subreddits/${subredditName}/threads`, { method: 'POST', body: JSON.stringify(data) });
export const getThreadCosts = (threadId: string) => request<import('@/types/platform').CostSummary>(`/threads/${threadId}/costs`);

// Agents
export const getAgents = () => request<import('@/types/platform').Agent[]>('/agents');
export const getAgent = (agentId: string) => request<import('@/types/platform').AgentDetail>(`/agents/${agentId}`);

// Deliberations
export const getDeliberation = (sessionId: string) => request<{ id: string; hypothesis: string; status: string; phase: string; post_count: number; energy_history: import('@/types/deliberation').EnergyUpdate[] }>(`/deliberations/${sessionId}`);
export const getDeliberationHistory = (sessionId: string) => request<{
  session: { id: string; hypothesis: string; status: string; phase: string };
  posts: import('@/types/deliberation').Post[];
  energy_history: import('@/types/deliberation').EnergyUpdate[];
  consensus: import('@/types/deliberation').ConsensusMap | null;
}>(`/deliberations/${sessionId}/history`);
export const getDeliberationPosts = (sessionId: string) => request<{ posts: import('@/types/deliberation').Post[] }>(`/deliberations/${sessionId}/posts`);
export const createDeliberation = (data: { hypothesis: string; mode?: string; max_turns?: number }) => request<{ id: string; hypothesis: string; status: string }>('/deliberations', { method: 'POST', body: JSON.stringify(data) });
export const interveneDeliberation = (sessionId: string, data: { type: string; content: string }) => request<{ posts: import('@/types/deliberation').Post[] }>(`/deliberations/${sessionId}/intervene`, { method: 'POST', body: JSON.stringify(data) });

// Memories
export const getMemories = (subredditName?: string) => {
  const params = subredditName ? `?subreddit=${subredditName}` : '';
  return request<{ memories: import('@/types/platform').Memory[]; total: number }>(`/memories${params}`);
};
export const getMemory = (memoryId: string) => request<import('@/types/platform').Memory>(`/memories/${memoryId}`);
export const annotateMemory = (memoryId: string, data: { annotation_type: string; content: string; created_by: string }) => request<import('@/types/platform').MemoryAnnotation>(`/memories/${memoryId}/annotate`, { method: 'POST', body: JSON.stringify(data) });
export const getSubredditMemories = (subredditName: string) => request<{ memories: import('@/types/platform').Memory[]; total: number }>(`/subreddits/${subredditName}/memories`);
export const getMemoryGraph = () => request<{ memories: import('@/types/platform').Memory[]; cross_references: import('@/types/platform').CrossReference[] }>('/memories/graph');

// Watchers
export const getWatchers = (subredditName: string) => request<{ watchers: import('@/types/platform').Watcher[]; total: number }>(`/subreddits/${subredditName}/watchers`);
export const createWatcher = (subredditName: string, data: {
  watcher_type: string; name: string; description: string; query: string; poll_interval_seconds?: number;
}) => request<import('@/types/platform').Watcher>(`/subreddits/${subredditName}/watchers`, { method: 'POST', body: JSON.stringify(data) });
export const deleteWatcher = (watcherId: string) => request<void>(`/watchers/${watcherId}`, { method: 'DELETE' });

// Notifications
export const getNotifications = (params?: { subreddit?: string; status?: string }) => {
  const searchParams = new URLSearchParams();
  if (params?.subreddit) searchParams.set('subreddit', params.subreddit);
  if (params?.status) searchParams.set('status', params.status);
  const qs = searchParams.toString();
  return request<{ notifications: import('@/types/platform').Notification[]; total: number }>(`/notifications${qs ? `?${qs}` : ''}`);
};
export const actOnNotification = (notificationId: string, data: { action: string; hypothesis?: string }) => request<import('@/types/platform').Notification>(`/notifications/${notificationId}/act`, { method: 'POST', body: JSON.stringify(data) });

// Export
export const exportMarkdown = async (threadId: string): Promise<string> => {
  const res = await fetch(`${API_BASE}/threads/${threadId}/export/markdown`);
  if (!res.ok) throw new Error('Export failed');
  return res.text();
};
export const exportJson = (threadId: string) => request<Record<string, unknown>>(`/threads/${threadId}/export/json`);

// Feedback / Calibration
export const reportOutcome = (threadId: string, data: import('@/types/platform').OutcomeReport) => request<unknown>(`/threads/${threadId}/outcome`, { method: 'POST', body: JSON.stringify(data) });
export const getAgentCalibration = (agentId: string) => request<import('@/types/platform').CalibrationReport>(`/agents/${agentId}/calibration`);
export const getCalibrationOverview = () => request<import('@/types/platform').CalibrationOverview>('/calibration/overview');

// ---------------------------------------------------------------------------
// Phase 6: Mission, budgets, org chart, approvals
// ---------------------------------------------------------------------------

import type {
  ApprovalRequest,
  ApprovalRequestType,
  ApprovalStatus,
  BudgetSummary,
  MissionObjective,
  OrgChart,
  SubredditMission,
  ObjectiveProgress,
} from '@/types/dashboards';

export const getSubredditMission = (name: string) =>
  request<SubredditMission>(`/subreddits/${name}/mission`);

export const updateSubredditMission = (
  name: string,
  data: { mission_md: string | null; objectives?: MissionObjective[]; regenerate_objectives?: boolean },
) =>
  request<SubredditMission>(`/subreddits/${name}/mission`, {
    method: 'PUT',
    body: JSON.stringify(data),
  });

export const getSubredditMissionProgress = (name: string) =>
  request<{ objectives: ObjectiveProgress[] }>(`/subreddits/${name}/mission/progress`);

export const getSubredditBudgets = (name: string) =>
  request<BudgetSummary>(`/subreddits/${name}/budgets`);

export const updateMemberBudget = (
  name: string,
  agentId: string,
  data: { max_cost_per_thread_usd?: number | null; monthly_budget_usd?: number | null },
) =>
  request<Record<string, unknown>>(
    `/subreddits/${name}/members/${agentId}/budget`,
    { method: 'PATCH', body: JSON.stringify(data) },
  );

export const getSubredditOrgChart = (name: string) =>
  request<OrgChart>(`/subreddits/${name}/org-chart`);

export const listSubredditApprovals = (name: string, status?: ApprovalStatus | 'all') => {
  const qs = status && status !== 'all' ? `?status=${status}` : '';
  return request<{ approvals: ApprovalRequest[] }>(`/subreddits/${name}/approvals${qs}`);
};

export const createSubredditApproval = (
  name: string,
  data: {
    request_type: ApprovalRequestType;
    initiator?: string;
    target_ref?: string | null;
    payload?: Record<string, unknown>;
    reason?: string;
    estimated_cost_usd?: number;
  },
) =>
  request<ApprovalRequest>(`/subreddits/${name}/approvals`, {
    method: 'POST',
    body: JSON.stringify(data),
  });

export const resolveApproval = (
  requestId: string,
  data: { status: ApprovalStatus; decided_by?: string },
) =>
  request<ApprovalRequest>(`/approvals/${requestId}/resolve`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
