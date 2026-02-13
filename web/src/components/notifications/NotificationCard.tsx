import { Link } from '@tanstack/react-router';
import { Play, X, ExternalLink } from 'lucide-react';
import { cn, timeAgo } from '@/lib/utils';
import type { Notification } from '@/types/platform';
import { SignalBadge } from '@/components/shared/SignalBadge';
import { StatusBadge } from '@/components/shared/StatusBadge';
import { Button } from '@/components/ui/button';

interface NotificationCardProps {
  notification: Notification;
  onAct: (id: string, action: string) => void;
}

export function NotificationCard({ notification, onAct }: NotificationCardProps) {
  const isPending = notification.status === 'pending';
  const isActed = notification.status === 'acted';

  return (
    <div
      className={cn(
        'rounded-lg border border-border-default bg-bg-surface p-5',
        'transition-all duration-200 ease-out',
        isPending && 'border-l-2 border-l-accent',
      )}
    >
      {/* Header row */}
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <SignalBadge signal={notification.signal} />
            <StatusBadge status={notification.status} />
          </div>
          <h3 className="mt-2 font-semibold text-text-primary line-clamp-2">
            {notification.title}
          </h3>
        </div>
      </div>

      {/* Summary */}
      <p className="mt-2 text-sm text-text-secondary line-clamp-3">
        {notification.summary}
      </p>

      {/* Suggested hypothesis */}
      {notification.suggested_hypothesis && (
        <p className="mt-2 text-sm italic text-text-accent line-clamp-2">
          &ldquo;{notification.suggested_hypothesis}&rdquo;
        </p>
      )}

      {/* Actions for pending notifications */}
      {isPending && (
        <div className="mt-4 flex items-center gap-2">
          <Button
            size="sm"
            onClick={() => onAct(notification.id, 'start_thread')}
          >
            <Play className="h-3.5 w-3.5" />
            Start Thread
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => onAct(notification.id, 'dismiss')}
          >
            <X className="h-3.5 w-3.5" />
            Dismiss
          </Button>
        </div>
      )}

      {/* Acted state */}
      {isActed && (
        <div className="mt-3 flex items-center gap-2 text-sm">
          {notification.action_taken && (
            <span className="text-text-secondary">
              Action: <span className="font-medium text-text-primary">{notification.action_taken}</span>
            </span>
          )}
          {notification.thread_id && (
            <Link
              to="/c/$name"
              params={{ name: notification.subreddit_id }}
              className="inline-flex items-center gap-1 text-xs font-medium text-text-accent hover:underline"
            >
              <ExternalLink className="h-3 w-3" />
              View Thread
            </Link>
          )}
        </div>
      )}

      {/* Timestamp */}
      <div className="mt-3 flex items-center justify-between text-xs text-text-muted">
        <span>{timeAgo(notification.created_at)}</span>
        {notification.acted_at && (
          <span>Acted {timeAgo(notification.acted_at)}</span>
        )}
      </div>
    </div>
  );
}
