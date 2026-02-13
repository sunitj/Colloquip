import { useState, useMemo } from 'react';
import { createFileRoute } from '@tanstack/react-router';
import { useQuery } from '@tanstack/react-query';
import { Search, Bot } from 'lucide-react';
import { getAgents } from '@/lib/api';
import { queryKeys } from '@/lib/queryKeys';
import { PageHeader } from '@/components/layout/PageHeader';
import { AgentCard } from '@/components/agents/AgentCard';
import { EmptyState } from '@/components/shared/EmptyState';
import { AnimatedList, AnimatedItem } from '@/components/shared/AnimatedList';
import { Input } from '@/components/ui/input';
import { Skeleton } from '@/components/ui/skeleton';

export const Route = createFileRoute('/agents/')({
  component: AgentPoolPage,
});

function AgentCardSkeleton() {
  return (
    <div className="rounded-lg border border-border-default bg-bg-surface p-5 space-y-3 flex flex-col items-center">
      <Skeleton className="h-16 w-16 rounded-full" />
      <Skeleton className="h-5 w-32" />
      <Skeleton className="h-4 w-20" />
      <div className="flex gap-1.5">
        <Skeleton className="h-5 w-14 rounded-full" />
        <Skeleton className="h-5 w-16 rounded-full" />
        <Skeleton className="h-5 w-12 rounded-full" />
      </div>
      <Skeleton className="h-3 w-24" />
    </div>
  );
}

function AgentPoolPage() {
  const [search, setSearch] = useState('');

  const agentsQuery = useQuery({
    queryKey: queryKeys.agents.all,
    queryFn: () => getAgents(),
  });

  const agents = agentsQuery.data ?? [];

  const filtered = useMemo(() => {
    if (!search.trim()) return agents;
    const q = search.toLowerCase();
    return agents.filter(
      (a) =>
        a.display_name.toLowerCase().includes(q) ||
        a.agent_type.toLowerCase().includes(q) ||
        a.expertise_tags.some((t) => t.toLowerCase().includes(q)),
    );
  }, [agents, search]);

  return (
    <div>
      <PageHeader
        title="Agent Pool"
        subtitle={
          agents.length > 0
            ? `${agents.length} agent${agents.length === 1 ? '' : 's'} registered`
            : undefined
        }
      />

      {/* Search */}
      <div className="relative mb-6 max-w-md">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-text-muted" />
        <Input
          placeholder="Search agents by name, type, or expertise..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="pl-9"
        />
      </div>

      {/* Content */}
      {agentsQuery.isLoading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {Array.from({ length: 6 }).map((_, i) => (
            <AgentCardSkeleton key={i} />
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <EmptyState
          icon={<Bot className="h-10 w-10" />}
          title={search ? 'No agents match your search' : 'No agents yet'}
          description={
            search
              ? 'Try adjusting your search terms.'
              : 'Agents will appear here once they are registered in the platform.'
          }
        />
      ) : (
        <AnimatedList className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {filtered.map((agent) => (
            <AnimatedItem key={agent.id}>
              <AgentCard agent={agent} />
            </AnimatedItem>
          ))}
        </AnimatedList>
      )}
    </div>
  );
}
