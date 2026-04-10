/**
 * Phase 6 dashboard data hooks — mission, budgets, org chart, approvals.
 * Each wraps TanStack Query with a 30s staleTime so the dashboards feel live
 * but don't hammer the API.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  getSubredditBudgets,
  getSubredditMission,
  getSubredditMissionProgress,
  getSubredditOrgChart,
  listSubredditApprovals,
  resolveApproval,
  updateMemberBudget,
  updateSubredditMission,
} from '@/lib/api';
import { queryKeys } from '@/lib/queryKeys';
import type {
  ApprovalStatus,
  MissionObjective,
} from '@/types/dashboards';

const STALE_30S = 30_000;

export function useSubredditMission(name: string | undefined) {
  return useQuery({
    queryKey: name ? queryKeys.dashboards.mission(name) : ['subreddits', 'mission', 'none'],
    queryFn: () => getSubredditMission(name!),
    enabled: !!name,
    staleTime: STALE_30S,
  });
}

export function useMissionProgress(name: string | undefined) {
  return useQuery({
    queryKey: name
      ? queryKeys.dashboards.missionProgress(name)
      : ['subreddits', 'mission-progress', 'none'],
    queryFn: () => getSubredditMissionProgress(name!),
    enabled: !!name,
    staleTime: STALE_30S,
  });
}

export function useUpdateMission(name: string | undefined) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: {
      mission_md: string | null;
      objectives?: MissionObjective[];
      regenerate_objectives?: boolean;
    }) => {
      if (!name) throw new Error('Subreddit name required');
      return updateSubredditMission(name, data);
    },
    onSuccess: () => {
      if (!name) return;
      qc.invalidateQueries({ queryKey: queryKeys.dashboards.mission(name) });
      qc.invalidateQueries({ queryKey: queryKeys.dashboards.missionProgress(name) });
    },
  });
}

export function useSubredditBudgets(name: string | undefined) {
  return useQuery({
    queryKey: name ? queryKeys.dashboards.budgets(name) : ['subreddits', 'budgets', 'none'],
    queryFn: () => getSubredditBudgets(name!),
    enabled: !!name,
    staleTime: STALE_30S,
  });
}

export function useUpdateMemberBudget(name: string | undefined) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      agentId,
      max_cost_per_thread_usd,
      monthly_budget_usd,
    }: {
      agentId: string;
      max_cost_per_thread_usd?: number | null;
      monthly_budget_usd?: number | null;
    }) => {
      if (!name) throw new Error('Subreddit name required');
      return updateMemberBudget(name, agentId, {
        max_cost_per_thread_usd,
        monthly_budget_usd,
      });
    },
    onSuccess: () => {
      if (!name) return;
      qc.invalidateQueries({ queryKey: queryKeys.dashboards.budgets(name) });
    },
  });
}

export function useOrgChart(name: string | undefined) {
  return useQuery({
    queryKey: name ? queryKeys.dashboards.orgChart(name) : ['subreddits', 'org-chart', 'none'],
    queryFn: () => getSubredditOrgChart(name!),
    enabled: !!name,
    staleTime: STALE_30S,
  });
}

export function useSubredditApprovals(
  name: string | undefined,
  status: ApprovalStatus | 'all' = 'pending',
) {
  return useQuery({
    queryKey: name
      ? queryKeys.dashboards.approvals(name, status)
      : ['subreddits', 'approvals', 'none'],
    queryFn: () => listSubredditApprovals(name!, status === 'all' ? undefined : status),
    enabled: !!name,
    staleTime: STALE_30S,
    refetchInterval: 15_000,
  });
}

export function useResolveApproval(name: string | undefined) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      requestId,
      status,
      decidedBy,
    }: {
      requestId: string;
      status: ApprovalStatus;
      decidedBy?: string;
    }) =>
      resolveApproval(requestId, {
        status,
        decided_by: decidedBy,
      }),
    onSuccess: () => {
      if (!name) return;
      qc.invalidateQueries({ queryKey: ['subreddits', name, 'approvals'] });
    },
  });
}
