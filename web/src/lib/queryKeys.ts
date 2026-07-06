export const queryKeys = {
  subreddits: {
    all: ['subreddits'] as const,
    detail: (name: string) => ['subreddits', name] as const,
    members: (name: string) => ['subreddits', name, 'members'] as const,
    threads: (name: string) => ['subreddits', name, 'threads'] as const,
    memories: (name: string) => ['subreddits', name, 'memories'] as const,
    watchers: (name: string) => ['subreddits', name, 'watchers'] as const,
  },
  agents: {
    all: ['agents'] as const,
    detail: (id: string) => ['agents', id] as const,
    calibration: (id: string) => ['agents', id, 'calibration'] as const,
  },
  deliberations: {
    detail: (id: string) => ['deliberations', id] as const,
    history: (id: string) => ['deliberations', id, 'history'] as const,
    posts: (id: string) => ['deliberations', id, 'posts'] as const,
  },
  threads: {
    costs: (id: string) => ['threads', id, 'costs'] as const,
  },
  memories: {
    all: (subreddit?: string) => subreddit ? ['memories', subreddit] : ['memories'] as const,
    detail: (id: string) => ['memories', id] as const,
    graph: ['memories', 'graph'] as const,
  },
  notifications: {
    all: (params?: { subreddit?: string; status?: string }) => ['notifications', params] as const,
  },
  calibration: {
    overview: ['calibration', 'overview'] as const,
  },
  // Phase 6 dashboards
  dashboards: {
    mission: (name: string) => ['subreddits', name, 'mission'] as const,
    missionProgress: (name: string) => ['subreddits', name, 'mission', 'progress'] as const,
    budgets: (name: string) => ['subreddits', name, 'budgets'] as const,
    orgChart: (name: string) => ['subreddits', name, 'org-chart'] as const,
    approvals: (name: string, status?: string) =>
      ['subreddits', name, 'approvals', status ?? 'all'] as const,
  },
} as const;
