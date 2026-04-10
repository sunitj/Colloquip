import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { useResolveApproval, useSubredditApprovals } from '@/hooks/dashboards';
import type { ApprovalRequest } from '@/types/dashboards';

interface ApprovalQueuePanelProps {
  subredditName: string;
}

function requestTypeLabel(type: ApprovalRequest['request_type']): string {
  switch (type) {
    case 'thread_spawn':
      return 'Thread spawn';
    case 'tool_call':
      return 'Tool call';
    case 'budget_override':
      return 'Budget override';
    case 'autoresearch_run':
      return 'Autoresearch run';
    case 'agent_hire':
      return 'Agent hire';
    default:
      return type;
  }
}

export function ApprovalQueuePanel({ subredditName }: ApprovalQueuePanelProps) {
  const { data, isLoading } = useSubredditApprovals(subredditName, 'pending');
  const resolveMutation = useResolveApproval(subredditName);
  const pending = data?.approvals ?? [];

  const handleResolve = (req: ApprovalRequest, status: 'approved' | 'denied') => {
    resolveMutation.mutate({
      requestId: req.id,
      status,
      decidedBy: 'user:admin',
    });
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Approval Queue</CardTitle>
        <CardDescription>
          Paperclip-style human-in-loop queue. Watcher-spawned threads, expensive tool
          calls, budget overrides, and autoresearch runs over policy land here until
          resolved.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        {isLoading && <p className="text-sm text-text-muted">Loading…</p>}
        {!isLoading && pending.length === 0 && (
          <p className="text-sm text-text-muted">No pending approvals.</p>
        )}
        {pending.map((req) => (
          <div
            key={req.id}
            className="rounded-md border border-border-default p-3"
          >
            <div className="flex flex-wrap items-start justify-between gap-2">
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <Badge variant="outline">{requestTypeLabel(req.request_type)}</Badge>
                  <span className="text-xs text-text-muted">
                    from {req.initiator || 'system'}
                  </span>
                </div>
                {req.reason && (
                  <p className="mt-1 text-sm text-text-primary">{req.reason}</p>
                )}
                <p className="text-xs text-text-muted">
                  est. ${req.estimated_cost_usd.toFixed(4)} · requested{' '}
                  {new Date(req.requested_at).toLocaleString()}
                </p>
              </div>
              <div className="flex gap-2">
                <Button
                  size="sm"
                  variant="default"
                  onClick={() => handleResolve(req, 'approved')}
                  disabled={resolveMutation.isPending}
                >
                  Approve
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => handleResolve(req, 'denied')}
                  disabled={resolveMutation.isPending}
                >
                  Deny
                </Button>
              </div>
            </div>
          </div>
        ))}
        {resolveMutation.error && (
          <p className="text-sm text-state-danger">
            {(resolveMutation.error as Error).message}
          </p>
        )}
      </CardContent>
    </Card>
  );
}
