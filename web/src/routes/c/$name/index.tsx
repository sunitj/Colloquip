import { useState } from 'react';
import { createFileRoute, Link } from '@tanstack/react-router';
import { useQuery } from '@tanstack/react-query';
import { Plus, MessageSquare, Home } from 'lucide-react';
import { getSubreddit, getSubredditMembers, getSubredditThreads } from '@/lib/api';
import { queryKeys } from '@/lib/queryKeys';
import { PageHeader } from '@/components/layout/PageHeader';
import { CommunityHeader } from '@/components/communities/CommunityHeader';
import { CommunityMembersPanel } from '@/components/communities/CommunityMembersPanel';
import { CommunityWatchersPanel } from '@/components/communities/CommunityWatchersPanel';
import { ThreadCard } from '@/components/threads/ThreadCard';
import { EmptyState } from '@/components/shared/EmptyState';
import { AnimatedList, AnimatedItem } from '@/components/shared/AnimatedList';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { CreateThreadDialog } from '@/components/dialogs/CreateThreadDialog';

export const Route = createFileRoute('/c/$name/')({
  component: CommunityPage,
});

function ThreadsSkeleton() {
  return (
    <div className="space-y-3">
      {Array.from({ length: 4 }).map((_, i) => (
        <div
          key={i}
          className="rounded-radius-lg border border-border-default bg-bg-surface p-5 space-y-3"
          style={{ borderLeftWidth: 3, borderLeftColor: '#374151' }}
        >
          <Skeleton className="h-5 w-3/4" />
          <Skeleton className="h-4 w-full" />
          <div className="flex gap-3">
            <Skeleton className="h-5 w-16 rounded-full" />
            <Skeleton className="h-5 w-16 rounded-full" />
            <Skeleton className="h-5 w-20" />
          </div>
        </div>
      ))}
    </div>
  );
}

function CommunityHeaderSkeleton() {
  return (
    <div className="space-y-4">
      <div>
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-4 w-32 mt-2" />
      </div>
      <Skeleton className="h-4 w-96" />
      <div className="flex gap-2">
        <Skeleton className="h-6 w-20 rounded-full" />
        <Skeleton className="h-6 w-24 rounded-full" />
      </div>
      <div className="flex gap-6">
        <Skeleton className="h-4 w-24" />
        <Skeleton className="h-4 w-24" />
      </div>
    </div>
  );
}

function CommunityPage() {
  const { name } = Route.useParams();
  const [createThreadOpen, setCreateThreadOpen] = useState(false);

  const communityQuery = useQuery({
    queryKey: queryKeys.subreddits.detail(name),
    queryFn: () => getSubreddit(name),
  });

  const membersQuery = useQuery({
    queryKey: queryKeys.subreddits.members(name),
    queryFn: () => getSubredditMembers(name),
  });

  const threadsQuery = useQuery({
    queryKey: queryKeys.subreddits.threads(name),
    queryFn: () => getSubredditThreads(name),
  });

  const community = communityQuery.data;
  const members = membersQuery.data?.members ?? [];
  const threads = threadsQuery.data?.threads ?? [];

  return (
    <div>
      {/* Page header with breadcrumb */}
      <PageHeader
        title={community?.display_name ?? name}
        breadcrumb={
          <nav className="flex items-center gap-1.5 text-sm text-text-muted">
            <Link to="/" className="inline-flex items-center gap-1 hover:text-text-primary transition-colors">
              <Home className="h-3.5 w-3.5" />
              Home
            </Link>
            <span>/</span>
            <span className="text-text-secondary">c/{name}</span>
          </nav>
        }
      />

      {/* Community header */}
      <div className="mb-6">
        {communityQuery.isLoading ? (
          <CommunityHeaderSkeleton />
        ) : community ? (
          <CommunityHeader community={community} />
        ) : communityQuery.isError ? (
          <div className="text-sm text-destructive">
            Failed to load community details.
          </div>
        ) : null}
      </div>

      {/* Tabs: Threads, Members, Watchers */}
      <Tabs defaultValue="threads">
        <TabsList className="w-full">
          <TabsTrigger value="threads">
            Threads
            {threads.length > 0 && (
              <span className="ml-1.5 text-text-muted">({threads.length})</span>
            )}
          </TabsTrigger>
          <TabsTrigger value="members">
            Members
            {members.length > 0 && (
              <span className="ml-1.5 text-text-muted">({members.length})</span>
            )}
          </TabsTrigger>
          <TabsTrigger value="watchers">Watchers</TabsTrigger>
        </TabsList>

        {/* Threads tab */}
        <TabsContent value="threads">
          <div className="flex items-center justify-end mb-4">
            <Button size="sm" onClick={() => setCreateThreadOpen(true)}>
              <Plus className="h-4 w-4" />
              New Thread
            </Button>
          </div>

          {threadsQuery.isLoading ? (
            <ThreadsSkeleton />
          ) : threads.length === 0 ? (
            <EmptyState
              icon={<MessageSquare className="h-10 w-10" />}
              title="No threads yet"
              description="Start a deliberation thread to kick off AI-driven discussion in this community."
              action={
                <Button size="sm" onClick={() => setCreateThreadOpen(true)}>
                  <Plus className="h-4 w-4" />
                  Create First Thread
                </Button>
              }
            />
          ) : (
            <AnimatedList className="space-y-3">
              {threads.map((thread) => (
                <AnimatedItem key={thread.id}>
                  <ThreadCard thread={thread} communityName={name} />
                </AnimatedItem>
              ))}
            </AnimatedList>
          )}
        </TabsContent>

        {/* Members tab */}
        <TabsContent value="members">
          {membersQuery.isLoading ? (
            <div className="space-y-2">
              {Array.from({ length: 3 }).map((_, i) => (
                <div
                  key={i}
                  className="flex items-center gap-4 rounded-radius-lg border border-border-default bg-bg-surface p-4"
                >
                  <Skeleton className="h-10 w-10 rounded-full" />
                  <div className="flex-1 space-y-2">
                    <Skeleton className="h-4 w-40" />
                    <Skeleton className="h-3 w-60" />
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <CommunityMembersPanel members={members} />
          )}
        </TabsContent>

        {/* Watchers tab */}
        <TabsContent value="watchers">
          <CommunityWatchersPanel communityName={name} />
        </TabsContent>
      </Tabs>

      <CreateThreadDialog
        open={createThreadOpen}
        onOpenChange={setCreateThreadOpen}
        communityName={name}
      />
    </div>
  );
}
