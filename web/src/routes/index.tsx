import { createFileRoute } from '@tanstack/react-router';
import { useQuery } from '@tanstack/react-query';
import { getSubreddits } from '@/lib/api';
import { queryKeys } from '@/lib/queryKeys';
import { PageHeader } from '@/components/layout/PageHeader';
import { EmptyState } from '@/components/shared/EmptyState';
import { Card, CardTitle, CardDescription } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Link } from '@tanstack/react-router';

export const Route = createFileRoute('/')({
  component: HomePage,
});

function HomePage() {
  const { data, isLoading } = useQuery({
    queryKey: queryKeys.subreddits.all,
    queryFn: getSubreddits,
  });

  const subreddits = data?.subreddits ?? [];

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <PageHeader
        title="Home"
        subtitle="Browse communities and recent deliberations"
      />

      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-32 rounded-lg bg-bg-tertiary animate-pulse" />
          ))}
        </div>
      ) : subreddits.length === 0 ? (
        <EmptyState
          title="No communities yet"
          description="Initialize the platform or create your first community to get started."
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {subreddits.map((sub) => (
            <Link key={sub.name} to="/c/$name" params={{ name: sub.name }}>
              <Card hover className="h-full">
                <div className="flex items-center gap-2 mb-2">
                  <CardTitle>c/{sub.name}</CardTitle>
                  <Badge variant="outline">{sub.thinking_type}</Badge>
                </div>
                <CardDescription>{sub.description}</CardDescription>
                <div className="flex items-center gap-3 mt-3 text-xs text-text-muted">
                  <span>{sub.member_count} agents</span>
                  <span>{sub.thread_count} threads</span>
                  {sub.has_red_team && <Badge variant="critical">Red Team</Badge>}
                </div>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
