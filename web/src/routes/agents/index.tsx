import { useState } from 'react';
import { createFileRoute, Link } from '@tanstack/react-router';
import { useQuery } from '@tanstack/react-query';
import { getAgents } from '@/lib/api';
import { queryKeys } from '@/lib/queryKeys';
import { getAgentColor, getAgentInitials } from '@/lib/agentColors';
import { PageHeader } from '@/components/layout/PageHeader';
import { Badge } from '@/components/ui/Badge';
import { EmptyState } from '@/components/shared/EmptyState';
import { Skeleton } from '@/components/ui/Skeleton';

export const Route = createFileRoute('/agents/')({
  component: AgentPoolPage,
});

function AgentPoolPage() {
  const [search, setSearch] = useState('');

  const { data, isLoading } = useQuery({
    queryKey: queryKeys.agents.all,
    queryFn: getAgents,
  });

  const agents = data?.agents ?? [];
  const filtered = search
    ? agents.filter(
        (a) =>
          a.display_name.toLowerCase().includes(search.toLowerCase()) ||
          a.agent_type.toLowerCase().includes(search.toLowerCase()) ||
          a.expertise_tags.some((t) => t.toLowerCase().includes(search.toLowerCase())),
      )
    : agents;

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <PageHeader title="Agent Pool" subtitle="Browse and manage all deliberation agents" />

      {/* Search */}
      <div className="mb-6">
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search agents by name, type, or expertise..."
          className="w-full max-w-md bg-bg-tertiary text-text-primary text-sm rounded-lg border border-border-default px-4 py-2 placeholder:text-text-muted focus:outline-none focus:ring-1 focus:ring-accent"
        />
      </div>

      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <Skeleton key={i} className="h-40" />
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <EmptyState
          title={search ? 'No matching agents' : 'No agents yet'}
          description={search ? 'Try a different search term.' : 'Initialize the platform to create agents.'}
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filtered.map((agent) => {
            const color = getAgentColor(agent.agent_type, agent.is_red_team);
            const initials = getAgentInitials(agent.display_name);
            return (
              <Link key={agent.id} to="/agents/$agentId" params={{ agentId: agent.id }}>
                <div className="rounded-lg border border-border-subtle bg-bg-secondary p-4 hover:bg-bg-tertiary/50 hover:border-border-default transition-all h-full">
                  <div className="flex items-center gap-3 mb-3">
                    <div
                      className="w-10 h-10 rounded-full flex items-center justify-center text-sm font-bold text-white shrink-0"
                      style={{ backgroundColor: color }}
                    >
                      {initials}
                    </div>
                    <div className="min-w-0">
                      <div className="text-sm font-semibold text-text-primary truncate">
                        {agent.display_name}
                      </div>
                      <div className="text-[10px] text-text-muted">{agent.agent_type}</div>
                    </div>
                    {agent.is_red_team && <Badge variant="critical" className="ml-auto shrink-0">Red Team</Badge>}
                  </div>

                  {agent.expertise_tags.length > 0 && (
                    <div className="flex flex-wrap gap-1.5 mb-3">
                      {agent.expertise_tags.slice(0, 5).map((tag) => (
                        <span key={tag} className="text-[10px] px-1.5 py-0.5 rounded bg-bg-tertiary text-text-muted">
                          {tag}
                        </span>
                      ))}
                      {agent.expertise_tags.length > 5 && (
                        <span className="text-[10px] text-text-muted">+{agent.expertise_tags.length - 5}</span>
                      )}
                    </div>
                  )}

                  <div className="text-[11px] text-text-muted">
                    {agent.subreddit_count} {agent.subreddit_count === 1 ? 'community' : 'communities'}
                  </div>
                </div>
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
}
