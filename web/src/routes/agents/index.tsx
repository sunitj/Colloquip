import { useState } from 'react';
import { createFileRoute, Link } from '@tanstack/react-router';
import { useQuery } from '@tanstack/react-query';
import { getAgents } from '@/lib/api';
import { queryKeys } from '@/lib/queryKeys';
import { getAgentColor, getAgentTextColor, getAgentInitials } from '@/lib/agentColors';
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
    <div className="p-4 sm:p-6 md:p-8 lg:p-10 max-w-4xl mx-auto">
      <PageHeader title="Agent Pool" subtitle="Browse and manage all deliberation agents" />

      {/* Search */}
      <div className="mb-6">
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search agents by name, type, or expertise..."
          className="w-full bg-white text-text-primary text-sm rounded-xl border border-border-default px-4 py-2.5 placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-accent/20 focus:border-accent focus:bg-bg-secondary transition-all duration-200"
        />
      </div>

      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
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
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filtered.map((agent) => {
            const color = getAgentColor(agent.agent_type, agent.is_red_team);
            const textColor = getAgentTextColor(agent.agent_type, agent.is_red_team);
            const initials = getAgentInitials(agent.display_name);
            return (
              <Link key={agent.id} to="/agents/$agentId" params={{ agentId: agent.id }}>
                <div className="rounded-2xl bg-bg-secondary border border-border-default p-5 hover:border-border-accent transition-all duration-200 h-full cursor-pointer">
                  <div className="flex items-center gap-3 mb-3">
                    <div
                      className="w-10 h-10 rounded-full flex items-center justify-center text-sm font-bold shrink-0"
                      style={{ backgroundColor: `${color}25`, color: textColor }}
                    >
                      {initials}
                    </div>
                    <div className="min-w-0">
                      <div className="text-sm font-semibold text-text-primary truncate">
                        {agent.display_name}
                      </div>
                      <div className="text-xs text-text-muted">{agent.agent_type}</div>
                    </div>
                    {agent.is_red_team && <Badge variant="critical" className="ml-auto shrink-0">Red Team</Badge>}
                  </div>

                  {agent.expertise_tags.length > 0 && (
                    <div className="flex flex-wrap gap-1.5 mb-3">
                      {agent.expertise_tags.slice(0, 5).map((tag) => (
                        <span key={tag} className="text-xs px-2 py-0.5 rounded-full bg-bg-tertiary text-text-muted">
                          {tag}
                        </span>
                      ))}
                      {agent.expertise_tags.length > 5 && (
                        <span className="text-xs text-text-muted">+{agent.expertise_tags.length - 5}</span>
                      )}
                    </div>
                  )}

                  <div className="text-xs text-text-muted">
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
