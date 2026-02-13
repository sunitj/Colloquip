import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getWatchers, deleteWatcher } from '@/lib/api';
import { queryKeys } from '@/lib/queryKeys';
import { CreateWatcherDialog } from '@/components/dialogs/CreateWatcherDialog';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';

interface CommunityWatchersPanelProps {
  subredditName: string;
}

function formatPollInterval(seconds: number): string {
  if (seconds < 60) return `${seconds}s`;
  if (seconds < 3600) return `${Math.round(seconds / 60)} min`;
  if (seconds < 86400) {
    const hours = Math.round(seconds / 3600);
    return `${hours} hr${hours !== 1 ? 's' : ''}`;
  }
  const days = Math.round(seconds / 86400);
  return `${days} day${days !== 1 ? 's' : ''}`;
}

function truncate(text: string, maxLength: number): string {
  if (text.length <= maxLength) return text;
  return text.slice(0, maxLength) + '...';
}

export function CommunityWatchersPanel({ subredditName }: CommunityWatchersPanelProps) {
  const queryClient = useQueryClient();
  const [dialogOpen, setDialogOpen] = useState(false);

  const { data, isLoading } = useQuery({
    queryKey: queryKeys.subreddits.watchers(subredditName),
    queryFn: () => getWatchers(subredditName),
  });

  const deleteMutation = useMutation({
    mutationFn: (watcherId: string) => deleteWatcher(watcherId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.subreddits.watchers(subredditName) });
    },
  });

  const watchers = data?.watchers ?? [];

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <div className="text-[10px] font-bold uppercase tracking-widest text-text-muted">
          Watchers ({isLoading ? '--' : watchers.length})
        </div>
        <Button size="sm" variant="outline" onClick={() => setDialogOpen(true)}>
          Add Watcher
        </Button>
      </div>

      {isLoading ? (
        <div className="text-xs text-text-muted py-2 text-center">Loading...</div>
      ) : watchers.length === 0 ? (
        <div className="text-xs text-text-muted py-2 text-center">No watchers configured</div>
      ) : (
        <div className="space-y-2">
          {watchers.map((watcher) => (
            <div
              key={watcher.id}
              className="rounded-lg border border-border-subtle bg-bg-tertiary/50 p-3"
            >
              <div className="flex items-start justify-between gap-2">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-1.5 flex-wrap">
                    <span className="text-xs font-medium text-text-primary truncate">
                      {watcher.name}
                    </span>
                    <Badge variant="phase">{watcher.watcher_type}</Badge>
                    <Badge variant={watcher.enabled ? 'supportive' : 'neutral'}>
                      {watcher.enabled ? 'Enabled' : 'Disabled'}
                    </Badge>
                  </div>
                  {watcher.description && (
                    <div className="text-[10px] text-text-muted mt-1">
                      {watcher.description}
                    </div>
                  )}
                  <div className="text-[10px] text-text-muted mt-1 font-mono">
                    {truncate(watcher.query, 80)}
                  </div>
                  <div className="text-[10px] text-text-muted mt-1">
                    Poll every {formatPollInterval(watcher.poll_interval_seconds)}
                  </div>
                </div>
                <Button
                  size="sm"
                  variant="destructive"
                  onClick={() => deleteMutation.mutate(watcher.id)}
                  disabled={deleteMutation.isPending}
                >
                  Delete
                </Button>
              </div>
            </div>
          ))}
        </div>
      )}

      <CreateWatcherDialog
        open={dialogOpen}
        onClose={() => setDialogOpen(false)}
        subredditName={subredditName}
      />
    </div>
  );
}
