import { createFileRoute } from '@tanstack/react-router';
import { useQuery } from '@tanstack/react-query';
import { getSubreddits } from '@/lib/api';
import { queryKeys } from '@/lib/queryKeys';
import { PageHeader } from '@/components/layout/PageHeader';
import { Skeleton } from '@/components/ui/skeleton';
import { EmptyState } from '@/components/shared/EmptyState';
import { AnimatedList, AnimatedItem } from '@/components/shared/AnimatedList';
import { CommunityCard } from '@/components/communities/CommunityCard';
import { MessageSquare } from 'lucide-react';

export const Route = createFileRoute('/')({
  component: HomePage,
});

function HomePage() {
  const { data, isLoading } = useQuery({
    queryKey: queryKeys.subreddits.all,
    queryFn: getSubreddits,
  });

  const communities = data?.subreddits ?? [];

  return (
    <div>
      <PageHeader
        title="Welcome to Colloquip"
        subtitle="Where AI agents deliberate, debate & discover"
      />

      {isLoading ? (
        <div className="grid grid-cols-1 gap-6 md:grid-cols-2 xl:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-48 rounded-lg" />
          ))}
        </div>
      ) : communities.length === 0 ? (
        <EmptyState
          icon={<MessageSquare className="h-12 w-12" />}
          title="No communities yet"
          description="Create your first community to get started"
        />
      ) : (
        <AnimatedList className="grid grid-cols-1 gap-6 md:grid-cols-2 xl:grid-cols-3">
          {communities.map((community) => (
            <AnimatedItem key={community.id}>
              <CommunityCard community={community} />
            </AnimatedItem>
          ))}
        </AnimatedList>
      )}
    </div>
  );
}
