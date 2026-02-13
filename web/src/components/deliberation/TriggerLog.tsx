import { useState } from 'react';
import { cn } from '@/lib/utils';
import { getAgentColor, getAgentInitials, TRIGGER_COLORS } from '@/lib/agentColors';
import type { TriggerEntry } from '@/types/deliberation';

interface AgentInfo {
  agent_id: string;
  agent_type: string;
  display_name: string;
  is_red_team: boolean;
}

interface TriggerLogProps {
  triggers: TriggerEntry[];
  agents: AgentInfo[];
}

export function TriggerLog({ triggers, agents }: TriggerLogProps) {
  const [activeFilter, setActiveFilter] = useState<string | null>(null);

  const recent = [...triggers].reverse().slice(0, 30);

  if (recent.length === 0) {
    return (
      <div className="text-xs text-text-muted py-4 text-center">
        No triggers fired yet.
      </div>
    );
  }

  const filtered = activeFilter
    ? recent.filter((e) => e.agentId === activeFilter)
    : recent;

  return (
    <div className="space-y-3">
      {/* Filter chips */}
      <div className="flex flex-wrap gap-1.5">
        <button
          className={cn(
            'text-[10px] px-2 py-1 rounded-full border transition-colors',
            activeFilter === null
              ? 'border-accent text-accent bg-accent/10'
              : 'border-border-default text-text-muted hover:text-text-secondary',
          )}
          onClick={() => setActiveFilter(null)}
        >
          All
        </button>
        {agents.map((agent) => {
          const count = recent.filter((e) => e.agentId === agent.agent_id).length;
          if (count === 0) return null;
          const color = getAgentColor(agent.agent_type, agent.is_red_team);
          const initials = getAgentInitials(agent.display_name);
          return (
            <button
              key={agent.agent_id}
              className={cn(
                'text-[10px] px-2 py-1 rounded-full border transition-colors',
                activeFilter === agent.agent_id
                  ? 'bg-opacity-10'
                  : 'border-border-default text-text-muted hover:text-text-secondary',
              )}
              style={
                activeFilter === agent.agent_id
                  ? { borderColor: color, color, backgroundColor: `${color}15` }
                  : {}
              }
              onClick={() => setActiveFilter(activeFilter === agent.agent_id ? null : agent.agent_id)}
            >
              {initials} {count}
            </button>
          );
        })}
      </div>

      {/* Entries */}
      <div className="space-y-1 max-h-64 overflow-y-auto scrollbar-thin">
        {filtered.map((entry, i) => {
          const agent = agents.find(a => a.agent_id === entry.agentId);
          const color = agent ? getAgentColor(agent.agent_type, agent.is_red_team) : '#94a3b8';
          return (
            <div key={i} className="flex items-center gap-2 text-[11px] py-1">
              <span className="font-medium shrink-0" style={{ color }}>
                {entry.agentName}
              </span>
              <span className="text-text-muted shrink-0">#{entry.postIndex + 1}</span>
              <div className="flex flex-wrap gap-1">
                {entry.rules.map((rule) => (
                  <span
                    key={rule}
                    className="px-1.5 py-0.5 rounded border text-text-muted"
                    style={{ borderColor: TRIGGER_COLORS[rule] || '#64748b' }}
                  >
                    {rule.replace(/_/g, ' ')}
                  </span>
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
