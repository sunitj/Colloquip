import { Link } from '@tanstack/react-router';
import { Users, MessageSquare } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { Subreddit } from '@/types/platform';

interface CommunityCardProps {
  community: Subreddit;
}

export function CommunityCard({ community }: CommunityCardProps) {
  return (
    <Link
      to="/c/$name"
      params={{ name: community.name }}
      className={cn(
        'group block rounded-lg border border-border-default bg-bg-surface p-5',
        'transition-all duration-200 ease-out',
        'hover:-translate-y-0.5 hover:border-border-accent hover:shadow-md',
      )}
    >
      {/* Header row */}
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <h3 className="text-lg font-semibold text-text-primary truncate">
            {community.display_name}
          </h3>
          <p className="text-sm text-text-secondary truncate">
            c/{community.name}
          </p>
        </div>

        <span className="shrink-0 rounded-sm bg-bg-elevated px-2 py-0.5 text-xs text-text-muted">
          {community.thinking_type}
        </span>
      </div>

      {/* Description */}
      {community.description && (
        <p className="mt-3 text-sm text-text-muted line-clamp-2">
          {community.description}
        </p>
      )}

      {/* Stats row */}
      <div className="mt-4 flex items-center gap-4 text-xs text-text-muted">
        <span className="inline-flex items-center gap-1">
          <Users className="h-3.5 w-3.5" />
          {community.member_count} {community.member_count === 1 ? 'agent' : 'agents'}
        </span>
        <span className="inline-flex items-center gap-1">
          <MessageSquare className="h-3.5 w-3.5" />
          {community.thread_count} {community.thread_count === 1 ? 'thread' : 'threads'}
        </span>

        {community.has_red_team && (
          <span className="ml-auto inline-flex items-center gap-1">
            <span className="inline-block h-2 w-2 rounded-full bg-[#EF4444]" />
            <span className="text-text-muted">Red team</span>
          </span>
        )}
      </div>
    </Link>
  );
}
