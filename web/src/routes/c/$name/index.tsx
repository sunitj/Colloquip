import { useState } from 'react';
import { createFileRoute } from '@tanstack/react-router';
import { useQuery } from '@tanstack/react-query';
import { getSubreddit, getSubredditThreads } from '@/lib/api';
import { queryKeys } from '@/lib/queryKeys';
import { CommunityHeader } from '@/components/communities/CommunityHeader';
import { CommunityMembersPanel } from '@/components/communities/CommunityMembersPanel';
import { CommunityWatchersPanel } from '@/components/communities/CommunityWatchersPanel';
import { ThreadCard } from '@/components/threads/ThreadCard';
import { CreateThreadDialog } from '@/components/dialogs/CreateThreadDialog';
import { EmptyState } from '@/components/shared/EmptyState';
import { RightPanel } from '@/components/layout/RightPanel';
import { Button } from '@/components/ui/Button';
import { Skeleton } from '@/components/ui/Skeleton';

export const Route = createFileRoute('/c/$name/')({
  component: CommunityPage,
});

function CommunityPage() {
  const { name } = Route.useParams();
  const [showCreateThread, setShowCreateThread] = useState(false);

  const { data: community, isLoading: loadingCommunity } = useQuery({
    queryKey: queryKeys.subreddits.detail(name),
    queryFn: () => getSubreddit(name),
  });

  const { data: threadsData, isLoading: loadingThreads } = useQuery({
    queryKey: queryKeys.subreddits.threads(name),
    queryFn: () => getSubredditThreads(name),
  });

  const threads = threadsData?.threads ?? [];
  const members = community?.members ?? [];

  return (
    <div className="flex gap-8 p-8 max-w-7xl mx-auto">
      {/* Main content */}
      <div className="flex-1 min-w-0">
        {loadingCommunity ? (
          <div className="space-y-3">
            <Skeleton className="h-8 w-48" />
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-2/3" />
          </div>
        ) : community ? (
          <CommunityHeader community={community} />
        ) : null}

        <div className="mt-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-base font-semibold text-text-primary">
              Threads
            </h2>
            <Button size="sm" onClick={() => setShowCreateThread(true)}>
              New Thread
            </Button>
          </div>

          {loadingThreads ? (
            <div className="space-y-4">
              {[1, 2, 3].map((i) => (
                <Skeleton key={i} className="h-28 w-full" />
              ))}
            </div>
          ) : threads.length === 0 ? (
            <EmptyState
              title="No threads yet"
              description="Start a new deliberation thread to get the conversation going."
            />
          ) : (
            <div className="space-y-4">
              {threads.map((thread) => (
                <ThreadCard key={thread.id} thread={thread} />
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Right sidebar */}
      <RightPanel>
        {loadingCommunity ? (
          <div className="space-y-3">
            {[1, 2, 3].map((i) => (
              <Skeleton key={i} className="h-16 w-full" />
            ))}
          </div>
        ) : (
          <>
            <CommunityMembersPanel members={members} />
            <CommunityWatchersPanel subredditName={name} />
          </>
        )}
      </RightPanel>

      <CreateThreadDialog
        open={showCreateThread}
        onClose={() => setShowCreateThread(false)}
        subredditName={name}
      />
    </div>
  );
}
