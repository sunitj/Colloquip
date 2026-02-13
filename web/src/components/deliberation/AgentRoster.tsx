import { cn } from '@/lib/utils';
import { getAgentColor, getAgentBgColor, getAgentInitials, STANCE_COLORS } from '@/lib/agentColors';
import type { Post, TriggerEntry } from '@/types/deliberation';

interface AgentInfo {
  agent_id: string;
  agent_type: string;
  display_name: string;
  is_red_team: boolean;
}

interface AgentRosterProps {
  agents: AgentInfo[];
  posts: Post[];
  triggers: TriggerEntry[];
  status: string;
}

export function AgentRoster({ agents, posts, triggers, status }: AgentRosterProps) {
  const postCounts: Record<string, number> = {};
  const lastStance: Record<string, string> = {};
  for (const post of posts) {
    postCounts[post.agent_id] = (postCounts[post.agent_id] || 0) + 1;
    lastStance[post.agent_id] = post.stance;
  }

  const lastTrigger: Record<string, string[]> = {};
  for (const t of triggers) {
    lastTrigger[t.agentId] = t.rules;
  }

  const recentAgents = posts.slice(-2).map(p => p.agent_id);
  const refractoryAgents = posts.slice(-4, -2).map(p => p.agent_id);

  return (
    <div className="space-y-3">
      {agents.map((agent) => {
        const color = getAgentColor(agent.agent_type, agent.is_red_team);
        const bgColor = getAgentBgColor(color);
        const initials = getAgentInitials(agent.display_name);
        const count = postCounts[agent.agent_id] || 0;
        const stance = lastStance[agent.agent_id];
        const isActive = status === 'running' && recentAgents.includes(agent.agent_id);
        const isRefractory = status === 'running' && refractoryAgents.includes(agent.agent_id);
        const trigger = lastTrigger[agent.agent_id];

        return (
          <div
            key={agent.agent_id}
            className={cn(
              'rounded-xl border-l-2 p-3 transition-all',
              isActive && 'ring-1 ring-accent/30',
            )}
            style={{ borderLeftColor: color, backgroundColor: bgColor }}
          >
            <div className="flex items-center gap-2 mb-1">
              <div
                className="w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold text-white shrink-0"
                style={{ backgroundColor: color }}
              >
                {initials}
              </div>
              <span className="text-sm font-medium truncate" style={{ color }}>
                {agent.display_name}
              </span>
              <span className={cn(
                'w-2 h-2 rounded-full ml-auto shrink-0',
                isActive ? 'bg-green-500 animate-pulse' : isRefractory ? 'bg-amber-500' : 'bg-gray-300',
              )} />
            </div>
            <div className="flex items-center gap-2 text-xs text-text-muted">
              <span>{count} posts</span>
              {stance && (
                <span style={{ color: STANCE_COLORS[stance] || '#6B7280' }}>
                  {stance.replace(/_/g, ' ')}
                </span>
              )}
            </div>
            {trigger && !trigger.includes('seed_phase') && (
              <div className="flex flex-wrap gap-1 mt-1.5">
                {trigger.map(r => (
                  <span key={r} className="text-xs px-1 py-0.5 rounded bg-bg-tertiary/50 text-text-muted">
                    {r.replace(/_/g, ' ')}
                  </span>
                ))}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
