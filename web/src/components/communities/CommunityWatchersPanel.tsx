import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Trash2, Eye, Clock, Webhook, BookOpen, Radio } from 'lucide-react';
import { cn } from '@/lib/utils';
import { timeAgo } from '@/lib/utils';
import { getWatchers, deleteWatcher } from '@/lib/api';
import { queryKeys } from '@/lib/queryKeys';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { EmptyState } from '@/components/shared/EmptyState';
import { AnimatedList, AnimatedItem } from '@/components/shared/AnimatedList';
import type { WatcherType } from '@/types/platform';

interface CommunityWatchersPanelProps {
  communityName: string;
}

const WATCHER_TYPE_ICONS: Record<WatcherType, React.ReactNode> = {
  literature: <BookOpen className="h-4 w-4" />,
  scheduled: <Clock className="h-4 w-4" />,
  webhook: <Webhook className="h-4 w-4" />,
};

function WatcherSkeleton() {
  return (
    <div className="space-y-3">
      {Array.from({ length: 3 }).map((_, i) => (
        <div
          key={i}
          className="flex items-center gap-4 rounded-radius-lg border border-border-default bg-bg-surface p-4"
        >
          <Skeleton className="h-8 w-8 rounded-full" />
          <div className="flex-1 space-y-2">
            <Skeleton className="h-4 w-40" />
            <Skeleton className="h-3 w-60" />
          </div>
          <Skeleton className="h-8 w-8 rounded-radius-md" />
        </div>
      ))}
    </div>
  );
}

export function CommunityWatchersPanel({ communityName }: CommunityWatchersPanelProps) {
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: queryKeys.subreddits.watchers(communityName),
    queryFn: () => getWatchers(communityName),
  });

  const deleteMutation = useMutation({
    mutationFn: deleteWatcher,
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.subreddits.watchers(communityName),
      });
    },
  });

  if (isLoading) {
    return <WatcherSkeleton />;
  }

  const watchers = data?.watchers ?? [];

  if (watchers.length === 0) {
    return (
      <EmptyState
        icon={<Eye className="h-10 w-10" />}
        title="No watchers configured"
        description="Watchers monitor external sources and surface new information for deliberation."
      />
    );
  }

  return (
    <AnimatedList className="space-y-2">
      {watchers.map((watcher) => (
        <AnimatedItem key={watcher.id}>
          <div
            className={cn(
              'flex items-start gap-4 rounded-radius-lg border border-border-default bg-bg-surface p-4',
              'transition-colors hover:bg-bg-elevated/30',
            )}
          >
            {/* Type icon */}
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-bg-elevated text-text-secondary">
              {WATCHER_TYPE_ICONS[watcher.watcher_type] ?? (
                <Radio className="h-4 w-4" />
              )}
            </div>

            {/* Content */}
            <div className="flex-1 min-w-0 space-y-1.5">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-sm font-semibold text-text-primary">
                  {watcher.name}
                </span>
                <Badge variant="secondary" className="text-[10px] px-1.5 py-0">
                  {watcher.watcher_type}
                </Badge>
                <Badge
                  variant={watcher.enabled ? 'success' : 'outline'}
                  className="text-[10px] px-1.5 py-0"
                >
                  {watcher.enabled ? 'Active' : 'Disabled'}
                </Badge>
              </div>

              {watcher.description && (
                <p className="text-xs text-text-secondary line-clamp-2">
                  {watcher.description}
                </p>
              )}

              <div className="flex items-center gap-4 text-xs text-text-muted">
                <span className="inline-flex items-center gap-1">
                  <Clock className="h-3 w-3" />
                  Every {Math.round(watcher.poll_interval_seconds / 60)}m
                </span>
                {watcher.query && (
                  <span className="truncate max-w-[200px]" title={watcher.query}>
                    Query: {watcher.query}
                  </span>
                )}
                <span>Created {timeAgo(watcher.created_at)}</span>
              </div>
            </div>

            {/* Delete button */}
            <Button
              variant="ghost"
              size="icon"
              className="shrink-0 text-text-muted hover:text-destructive"
              onClick={() => deleteMutation.mutate(watcher.id)}
              disabled={deleteMutation.isPending}
              aria-label={`Delete watcher ${watcher.name}`}
            >
              <Trash2 className="h-4 w-4" />
            </Button>
          </div>
        </AnimatedItem>
      ))}
    </AnimatedList>
  );
}
