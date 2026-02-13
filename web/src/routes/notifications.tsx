import { useState } from 'react';
import { createFileRoute, Link } from '@tanstack/react-router';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getNotifications, actOnNotification } from '@/lib/api';
import { queryKeys } from '@/lib/queryKeys';
import { PageHeader } from '@/components/layout/PageHeader';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { EmptyState } from '@/components/shared/EmptyState';
import { Skeleton } from '@/components/ui/Skeleton';
import { cn } from '@/lib/utils';
import { timeAgo } from '@/lib/utils';
import type { Notification, NotificationStatus, TriageSignal } from '@/types/platform';

export const Route = createFileRoute('/notifications')({
  component: NotificationsPage,
});

const FILTER_TABS: { label: string; value: NotificationStatus | undefined }[] = [
  { label: 'All', value: undefined },
  { label: 'Pending', value: 'pending' },
  { label: 'Acted', value: 'acted' },
  { label: 'Dismissed', value: 'dismissed' },
];

const signalBadgeVariant: Record<TriageSignal, 'critical' | 'neutral' | 'default'> = {
  high: 'critical',
  medium: 'neutral',
  low: 'default',
};

const statusBadgeVariant: Record<NotificationStatus, 'phase' | 'default' | 'supportive' | 'outline'> = {
  pending: 'phase',
  read: 'default',
  acted: 'supportive',
  dismissed: 'outline',
};

function NotificationsPage() {
  const [activeStatus, setActiveStatus] = useState<NotificationStatus | undefined>(undefined);
  const queryClient = useQueryClient();

  const params = activeStatus ? { status: activeStatus } : undefined;

  const { data, isLoading } = useQuery({
    queryKey: queryKeys.notifications.all(params),
    queryFn: () => getNotifications(params),
  });

  const notifications = data?.notifications ?? [];

  const actMutation = useMutation({
    mutationFn: ({ id, action, hypothesis }: { id: string; action: string; hypothesis?: string }) =>
      actOnNotification(id, { action, hypothesis }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.notifications.all() });
    },
  });

  return (
    <div className="p-4 sm:p-6 md:p-8 lg:p-10 max-w-4xl mx-auto">
      <PageHeader title="Notifications" subtitle="Watcher alerts and updates" />

      {/* Filter Tabs -- pill-in-container style */}
      <div className="inline-flex items-center gap-0.5 rounded-xl bg-bg-tertiary/50 p-1 mb-6">
        {FILTER_TABS.map((tab) => (
          <button
            key={tab.label}
            onClick={() => setActiveStatus(tab.value)}
            className={cn(
              'px-4 py-1.5 text-sm font-medium rounded-lg transition-all duration-200 cursor-pointer',
              activeStatus === tab.value
                ? 'bg-bg-secondary text-text-primary shadow-sm'
                : 'text-text-muted hover:text-text-secondary',
            )}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Content */}
      {isLoading ? (
        <div className="space-y-3">
          {[1, 2, 3, 4].map((i) => (
            <Skeleton key={i} className="h-36 w-full" />
          ))}
        </div>
      ) : notifications.length === 0 ? (
        <EmptyState
          title="No notifications"
          description={
            activeStatus
              ? `No ${activeStatus} notifications found.`
              : 'No notifications yet. Watchers will generate alerts here when they detect relevant events.'
          }
        />
      ) : (
        <div className="space-y-3">
          {notifications.map((notification) => (
            <NotificationCard
              key={notification.id}
              notification={notification}
              onAct={(action, hypothesis) =>
                actMutation.mutate({ id: notification.id, action, hypothesis })
              }
              isActing={actMutation.isPending}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function NotificationCard({
  notification,
  onAct,
  isActing,
}: {
  notification: Notification;
  onAct: (action: string, hypothesis?: string) => void;
  isActing: boolean;
}) {
  return (
    <div className={cn(
      'rounded-2xl bg-bg-secondary border border-border-default p-6',
      notification.signal === 'high' && 'border-l-4 border-l-pastel-rose',
      notification.signal === 'medium' && 'border-l-4 border-l-pastel-peach',
      notification.signal === 'low' && 'border-l-4 border-l-pastel-sky',
    )}>
      {/* Header row: title + badges + time */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2 min-w-0">
          <h3 className="text-sm font-bold text-text-primary truncate">{notification.title}</h3>
          <Badge variant={signalBadgeVariant[notification.signal]}>{notification.signal}</Badge>
          <Badge variant={statusBadgeVariant[notification.status]}>{notification.status}</Badge>
        </div>
        <span className="text-xs text-text-muted whitespace-nowrap shrink-0">
          {timeAgo(notification.created_at)}
        </span>
      </div>

      {/* Summary */}
      <p className="text-sm text-text-secondary mt-2">{notification.summary}</p>

      {/* Suggested hypothesis */}
      {notification.suggested_hypothesis && (
        <div className="mt-3 border-l-2 border-accent/30 pl-3 py-1">
          <p className="text-xs font-semibold text-text-secondary mb-1">
            Suggested Hypothesis
          </p>
          <p className="text-sm text-text-secondary italic">{notification.suggested_hypothesis}</p>
        </div>
      )}

      {/* Actions for pending notifications */}
      {notification.status === 'pending' && (
        <div className="flex items-center gap-2 mt-4">
          <Button
            size="sm"
            disabled={isActing}
            onClick={() =>
              onAct(
                'start_thread',
                notification.suggested_hypothesis ?? undefined,
              )
            }
          >
            Start Thread
          </Button>
          <Button
            size="sm"
            variant="ghost"
            disabled={isActing}
            onClick={() => onAct('dismiss')}
          >
            Dismiss
          </Button>
        </div>
      )}

      {/* Acted state */}
      {notification.status === 'acted' && (
        <div className="flex items-center gap-2 mt-4 text-xs text-text-secondary">
          <span>Thread started</span>
          {notification.thread_id && (
            <Link
              to="/c/$name/thread/$threadId"
              params={{ name: notification.subreddit_id, threadId: notification.thread_id }}
              className="text-accent hover:underline"
            >
              View thread
            </Link>
          )}
          {notification.acted_at && (
            <span className="text-text-muted">{timeAgo(notification.acted_at)}</span>
          )}
        </div>
      )}
    </div>
  );
}
