import type { TriggerEntry } from '../types/deliberation';
import { AGENT_META, TRIGGER_COLORS } from './agentMeta';

interface TriggerLogProps {
  triggers: TriggerEntry[];
}

export function TriggerLog({ triggers }: TriggerLogProps) {
  // Show most recent first, limit to 20
  const recent = [...triggers].reverse().slice(0, 20);

  if (recent.length === 0) {
    return (
      <div className="trigger-log">
        <h2 className="panel-title">Trigger Log</h2>
        <div className="trigger-empty">No triggers fired yet.</div>
      </div>
    );
  }

  return (
    <div className="trigger-log">
      <h2 className="panel-title">Trigger Log</h2>
      <div className="trigger-entries">
        {recent.map((entry, i) => {
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
