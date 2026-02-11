import { useState } from 'react';
import type { TriggerEntry } from '../types/deliberation';
import { AGENT_META, TRIGGER_COLORS } from './agentMeta';

interface TriggerLogProps {
  triggers: TriggerEntry[];
}

const FILTER_AGENTS = ['biology', 'chemistry', 'admet', 'clinical', 'regulatory', 'redteam'];

export function TriggerLog({ triggers }: TriggerLogProps) {
  const [activeFilter, setActiveFilter] = useState<string | null>(null);

  // Show most recent first, limit to 30
  const recent = [...triggers].reverse().slice(0, 30);

  if (recent.length === 0) {
    return (
      <div className="trigger-log">
        <h2 className="panel-title">Trigger Log</h2>
        <div className="trigger-empty">No triggers fired yet.</div>
      </div>
    );
  }

  const filtered = activeFilter
    ? recent.filter(e => e.agentId === activeFilter)
    : recent;

  return (
    <div className="trigger-log">
      <h2 className="panel-title">Trigger Log</h2>

      {/* Filter chips */}
      <div className="trigger-filters">
        <button
          className={`trigger-filter-chip ${activeFilter === null ? 'active' : ''}`}
          onClick={() => setActiveFilter(null)}
        >
          All
        </button>
        {FILTER_AGENTS.map(agentId => {
          const meta = AGENT_META[agentId];
          if (!meta) return null;
          const count = recent.filter(e => e.agentId === agentId).length;
          if (count === 0) return null;
          return (
            <button
              key={agentId}
              className={`trigger-filter-chip ${activeFilter === agentId ? 'active' : ''}`}
              style={activeFilter === agentId ? { borderColor: meta.color, color: meta.color } : {}}
              onClick={() => setActiveFilter(activeFilter === agentId ? null : agentId)}
            >
              {meta.icon} {count}
            </button>
          );
        })}
      </div>

      <div className="trigger-entries">
        {filtered.map((entry, i) => {
          const meta = AGENT_META[entry.agentId];
          return (
            <div key={i} className="trigger-entry">
              <span className="trigger-agent" style={{ color: meta?.color || '#94a3b8' }}>
                {meta?.icon || '?'} {entry.agentName}
              </span>
              <span className="trigger-post-num">#{entry.postIndex + 1}</span>
              <div className="trigger-rules">
                {entry.rules.map(rule => (
                  <span
                    key={rule}
                    className="trigger-rule-badge"
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
