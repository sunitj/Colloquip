import { useState } from 'react';
import { createFileRoute } from '@tanstack/react-router';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Bell } from 'lucide-react';
import { getNotifications, actOnNotification } from '@/lib/api';
import { queryKeys } from '@/lib/queryKeys';
import { PageHeader } from '@/components/layout/PageHeader';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { Skeleton } from '@/components/ui/skeleton';
import { EmptyState } from '@/components/shared/EmptyState';
import { AnimatedList, AnimatedItem } from '@/components/shared/AnimatedList';
import { NotificationCard } from '@/components/notifications/NotificationCard';

export const Route = createFileRoute('/notifications')({
  component: NotificationsPage,
});

type StatusTab = 'all' | 'pending' | 'acted' | 'dismissed';

function NotificationsPage() {
  const queryClient = useQueryClient();
  const [tab, setTab] = useState<StatusTab>('all');

  const statusParam = tab === 'all' ? undefined : tab;

  const { data, isLoading } = useQuery({
    queryKey: queryKeys.notifications.all(
      statusParam ? { status: statusParam } : undefined,
    ),
    queryFn: () => getNotifications(statusParam ? { status: statusParam } : undefined),
  });

  const notifications = data?.notifications ?? [];

  const actMutation = useMutation({
    mutationFn: ({ id, action }: { id: string; action: string }) =>
      actOnNotification(id, { action }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] });
    },
  });

  const handleAct = (id: string, action: string) => {
    actMutation.mutate({ id, action });
  };

  return (
    <div>
      <PageHeader
        title="Notifications"
        subtitle="Watcher-triggered events and actionable signals"
      />

      <Tabs
        value={tab}
        onValueChange={(v) => setTab(v as StatusTab)}
      >
        <TabsList className="mb-6">
          <TabsTrigger value="all">All</TabsTrigger>
          <TabsTrigger value="pending">Pending</TabsTrigger>
          <TabsTrigger value="acted">Acted</TabsTrigger>
          <TabsTrigger value="dismissed">Dismissed</TabsTrigger>
        </TabsList>

        <TabsContent value={tab}>
          {isLoading ? (
            <div className="space-y-4">
              {Array.from({ length: 4 }).map((_, i) => (
                <Skeleton key={i} className="h-40 rounded-lg" />
              ))}
            </div>
          ) : notifications.length === 0 ? (
            <EmptyState
              icon={<Bell className="h-12 w-12" />}
              title="No notifications"
              description={
                tab === 'all'
                  ? 'Notifications appear when watchers detect relevant events. Configure watchers on your communities.'
                  : `No ${tab} notifications at this time.`
              }
            />
          ) : (
            <AnimatedList className="space-y-4">
              {notifications.map((notification) => (
                <AnimatedItem key={notification.id}>
                  <NotificationCard
                    notification={notification}
                    onAct={handleAct}
                  />
                </AnimatedItem>
              ))}
            </AnimatedList>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}
