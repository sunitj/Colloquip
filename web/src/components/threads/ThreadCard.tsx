import { cn, timeAgo } from '@/lib/utils';
import { PHASE_COLORS, PHASE_LABELS } from '@/lib/agentColors';
import type { Thread } from '@/types/platform';
import { Link } from '@tanstack/react-router';

interface ThreadCardProps {
  thread: Thread;
}

const STATUS_STYLES: Record<string, string> = {
  active: 'text-pastel-mint',
  paused: 'text-pastel-lemon',
  completed: 'text-text-muted',
  failed: 'text-pastel-rose',
  cancelled: 'text-text-muted',
};

export function ThreadCard({ thread }: ThreadCardProps) {
  const phaseColor = PHASE_COLORS[thread.phase] || '#94A3B8';

  return (
    <Link
      to="/c/$name/thread/$threadId"
      params={{ name: thread.subreddit_name, threadId: thread.id }}
      className="block"
    >
      <div className="rounded-lg border border-border-subtle bg-bg-secondary p-5 border-l-2 hover:bg-bg-tertiary/50 hover:border-border-default transition-all" style={{ borderLeftColor: phaseColor }}>
        <div className="flex items-start justify-between gap-3 mb-2">
          <h3 className="text-sm font-semibold text-text-primary leading-snug">
            {thread.title}
          </h3>
          <span className={cn('text-xs font-semibold uppercase shrink-0', STATUS_STYLES[thread.status] || 'text-text-muted')}>
            {thread.status}
          </span>
        </div>

        <p className="text-xs text-text-secondary leading-relaxed mb-3 line-clamp-2">
          {thread.hypothesis}
        </p>

        <div className="flex items-center gap-3 text-xs text-text-muted">
          <span
            className="font-semibold uppercase tracking-wider"
            style={{ color: phaseColor }}
          >
            {PHASE_LABELS[thread.phase] || thread.phase}
          </span>
          <span>{thread.post_count} posts</span>
          {thread.estimated_cost_usd > 0 && (
            <span>${thread.estimated_cost_usd.toFixed(3)}</span>
          )}
          {thread.created_at && (
            <span className="ml-auto">{timeAgo(thread.created_at)}</span>
          )}
        </div>
      </div>
    </Link>
  );
}
