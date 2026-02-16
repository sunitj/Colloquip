import { Link } from '@tanstack/react-router';
import { MessageSquare, DollarSign } from 'lucide-react';
import { cn, timeAgo, formatCost } from '@/lib/utils';
import { PHASE_COLORS } from '@/lib/agentColors';
import { PhaseBadge } from '@/components/shared/PhaseBadge';
import { StatusBadge } from '@/components/shared/StatusBadge';
import type { Thread } from '@/types/platform';

interface ThreadCardProps {
  thread: Thread;
  communityName: string;
}

export function ThreadCard({ thread, communityName }: ThreadCardProps) {
  const phaseColor = PHASE_COLORS[thread.phase] ?? '#6B7280';
  const isLive = thread.status === 'active';

  return (
    <Link
      to="/c/$name/thread/$threadId"
      params={{ name: communityName, threadId: thread.id }}
      className={cn(
        'group block rounded-lg border border-border-default bg-bg-surface p-5',
        'transition-all duration-150',
        'hover:bg-bg-elevated/30',
      )}
      style={{
        borderLeftWidth: 3,
        borderLeftColor: phaseColor,
        borderLeftStyle: 'solid',
      }}
    >
      <div className="space-y-3">
        {/* Title row */}
        <div className="flex items-start justify-between gap-3">
          <h3 className="text-base font-semibold text-text-primary group-hover:text-text-accent transition-colors">
            {thread.title}
          </h3>
          {isLive && (
            <span className="inline-flex items-center gap-1.5 shrink-0">
              <span className="relative flex h-2 w-2">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-red-500 opacity-75" />
                <span className="relative inline-flex h-2 w-2 rounded-full bg-red-500" />
              </span>
              <span className="text-xs font-bold text-red-500 uppercase tracking-wider">
                Live
              </span>
            </span>
          )}
        </div>

        {/* Hypothesis */}
        {thread.hypothesis && (
          <p className="text-sm text-text-secondary line-clamp-2">
            {thread.hypothesis}
          </p>
        )}

        {/* Bottom metadata row */}
        <div className="flex items-center gap-3 flex-wrap">
          <PhaseBadge phase={thread.phase} />
          <StatusBadge status={thread.status} />

          <span className="inline-flex items-center gap-1 text-xs text-text-muted">
            <MessageSquare className="h-3 w-3" />
            {thread.post_count} post{thread.post_count !== 1 ? 's' : ''}
          </span>

          {thread.estimated_cost_usd > 0 && (
            <span className="inline-flex items-center gap-1 text-xs text-text-muted">
              <DollarSign className="h-3 w-3" />
              {formatCost(thread.estimated_cost_usd)}
            </span>
          )}

          {thread.created_at && (
            <span className="text-xs text-text-muted ml-auto">
              {timeAgo(thread.created_at)}
            </span>
          )}
        </div>
      </div>
    </Link>
  );
}
