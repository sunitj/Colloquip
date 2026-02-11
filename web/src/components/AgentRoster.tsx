import type { Post, TriggerEntry } from '../types/deliberation';
import { AGENT_META, STANCE_COLORS } from './agentMeta';

interface AgentRosterProps {
  posts: Post[];
  triggers: TriggerEntry[];
  status: string;
}

const AGENT_ORDER = ['biology', 'chemistry', 'admet', 'clinical', 'regulatory', 'redteam'];

const AGENT_DESCRIPTIONS: Record<string, string> = {
  biology: 'Evaluates biological plausibility, mechanisms, targets, and pathways',
  chemistry: 'Assesses chemical tractability, SAR, binding affinity, and synthesis',
  admet: 'Reviews drug safety, metabolism, toxicology, and therapeutic index',
  clinical: 'Focuses on patient relevance, trial design, and translational validity',
  regulatory: 'Analyzes regulatory precedent, approval pathways, and compliance',
  redteam: 'Challenges assumptions, surfaces biases, and prevents premature consensus',
};

export function AgentRoster({ posts, triggers, status }: AgentRosterProps) {
  const postCounts: Record<string, number> = {};
  const lastStance: Record<string, string> = {};
  for (const post of posts) {
    postCounts[post.agent_id] = (postCounts[post.agent_id] || 0) + 1;
    lastStance[post.agent_id] = post.stance;
  }

  // Last trigger per agent
  const lastTrigger: Record<string, string[]> = {};
  for (const t of triggers) {
    lastTrigger[t.agentId] = t.rules;
  }

  // Recent posters (last 2 posts) = active, last 2-4 = refractory, else idle
  const recentAgents = posts.slice(-2).map(p => p.agent_id);
  const refractoryAgents = posts.slice(-4, -2).map(p => p.agent_id);

  return (
    <div className="agent-roster">
      <h2 className="panel-title">Agents</h2>
      {AGENT_ORDER.map(agentId => {
        const meta = AGENT_META[agentId];
        if (!meta) return null;
        const count = postCounts[agentId] || 0;
        const stance = lastStance[agentId];
        const isActive = status === 'running' && recentAgents.includes(agentId);
        const isRefractory = status === 'running' && refractoryAgents.includes(agentId);
        const trigger = lastTrigger[agentId];

        let statusLabel = 'idle';
        let statusClass = 'idle';
        if (isActive) { statusLabel = 'active'; statusClass = 'active'; }
        else if (isRefractory) { statusLabel = 'refractory'; statusClass = 'refractory'; }

        return (
          <div
            key={agentId}
            className={`agent-card ${statusClass}`}
            style={{ borderLeftColor: meta.color }}
            title={AGENT_DESCRIPTIONS[agentId] || ''}
          >
            <div className="agent-header">
              <span className="agent-icon">{meta.icon}</span>
              <span className="agent-name" style={{ color: meta.color }}>{meta.name}</span>
              <span className={`agent-status-dot ${statusClass}`} title={statusLabel} />
            </div>
            <div className="agent-stats">
              <span className="agent-post-count">{count} posts</span>
              {stance && (
                <span
                  className="agent-stance-badge"
                  style={{ color: STANCE_COLORS[stance] }}
                >
                  {stance.replace(/_/g, ' ')}
                </span>
              )}
            </div>
            {trigger && !trigger.includes('seed_phase') && (
              <div className="agent-last-trigger">
                {trigger.map(r => (
                  <span key={r} className="trigger-tag">{r.replace(/_/g, ' ')}</span>
                ))}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
