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

// Research Programs & Jobs
export const getResearchProgram = (subredditName: string) =>
  request<import('@/types/platform').ResearchProgram>(`/subreddits/${subredditName}/research-program`);
export const updateResearchProgram = (subredditName: string, content: string) =>
  request<import('@/types/platform').ResearchProgram>(`/subreddits/${subredditName}/research-program`, {
    method: 'PUT', body: JSON.stringify({ content }),
  });
export const getResearchJobs = (subredditName: string) =>
  request<{ jobs: import('@/types/platform').ResearchJob[] }>(`/subreddits/${subredditName}/research-jobs`);
export const createResearchJob = (subredditName: string, data: {
  max_iterations?: number; max_cost_usd?: number; max_threads_per_hour?: number; max_runtime_hours?: number;
}) => request<import('@/types/platform').ResearchJob>(`/subreddits/${subredditName}/research-jobs`, {
  method: 'POST', body: JSON.stringify(data),
});
export const getResearchJob = (jobId: string) =>
  request<import('@/types/platform').ResearchJob>(`/research-jobs/${jobId}`);
export const pauseResearchJob = (jobId: string) =>
  request<import('@/types/platform').ResearchJob>(`/research-jobs/${jobId}/pause`, { method: 'POST' });
export const resumeResearchJob = (jobId: string) =>
  request<import('@/types/platform').ResearchJob>(`/research-jobs/${jobId}/resume`, { method: 'POST' });
export const stopResearchJob = (jobId: string) =>
  request<import('@/types/platform').ResearchJob>(`/research-jobs/${jobId}/stop`, { method: 'POST' });
export const getResearchJobResults = (jobId: string) =>
  request<{ job_id: string; iterations: import('@/types/platform').ResearchIteration[]; summary: Record<string, unknown> }>(`/research-jobs/${jobId}/results`);

// Jobs & Pipelines
export const getNfProcesses = (category?: string) => {
  const params = category ? `?category=${encodeURIComponent(category)}` : '';
  return request<{ processes: import('@/types/jobs').NextflowProcess[] }>(`/nf-processes${params}`);
};
export const getNfProcess = (processId: string) => request<import('@/types/jobs').NextflowProcess>(`/nf-processes/${processId}`);
export const getJobs = (sessionId?: string) => {
  const params = sessionId ? `?session_id=${sessionId}` : '';
  return request<{ jobs: import('@/types/jobs').Job[] }>(`/jobs${params}`);
};
export const getJob = (jobId: string) => request<import('@/types/jobs').Job>(`/jobs/${jobId}`);
export const createJob = (data: {
  session_id: string; agent_id: string; pipeline_name: string;
  pipeline_description?: string; steps: unknown[]; parameters?: Record<string, unknown>;
  compute_profile?: string; thread_id?: string;
}) => request<{ job_id: string; status: string; error?: string }>('/jobs', { method: 'POST', body: JSON.stringify(data) });
export const cancelJob = (jobId: string) => request<{ status: string }>(`/jobs/${jobId}/cancel`, { method: 'POST' });

// Proposals
export const getProposals = (sessionId: string) => request<{ proposals: import('@/types/jobs').ActionProposal[] }>(`/proposals?session_id=${sessionId}`);
export const reviewProposal = (proposalId: string, data: { reviewer: string; action: 'approve' | 'reject'; note?: string }) =>
  request<{ status: string; job_id?: string }>(`/proposals/${proposalId}/review`, { method: 'POST', body: JSON.stringify(data) });

// Data Connections
export const getDataConnections = (subredditId: string) => request<{ connections: import('@/types/jobs').DataConnection[] }>(`/subreddits/${subredditId}/data-connections`);
export const createDataConnection = (subredditId: string, data: {
  name: string; description?: string; db_type?: string; connection_string: string; read_only?: boolean;
}) => request<import('@/types/jobs').DataConnection>(`/subreddits/${subredditId}/data-connections`, { method: 'POST', body: JSON.stringify(data) });
export const deleteDataConnection = (subredditId: string, connId: string) =>
  request<{ status: string }>(`/subreddits/${subredditId}/data-connections/${connId}`, { method: 'DELETE' });
