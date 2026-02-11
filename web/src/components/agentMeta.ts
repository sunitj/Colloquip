/** Agent display metadata */

export interface AgentMeta {
  name: string;
  color: string;
  bgColor: string;
  icon: string;
}

export const AGENT_META: Record<string, AgentMeta> = {
  biology: {
    name: 'Biology & Target ID',
    color: '#22c55e',
    bgColor: '#22c55e18',
    icon: '🧬',
  },
  chemistry: {
    name: 'Discovery Chemistry',
    color: '#3b82f6',
    bgColor: '#3b82f618',
    icon: '⚗️',
  },
  admet: {
    name: 'ADMET & Toxicology',
    color: '#f59e0b',
    bgColor: '#f59e0b18',
    icon: '🛡️',
  },
  clinical: {
    name: 'Clinical Translation',
    color: '#8b5cf6',
    bgColor: '#8b5cf618',
    icon: '🏥',
  },
  regulatory: {
    name: 'Regulatory Strategy',
    color: '#06b6d4',
    bgColor: '#06b6d418',
    icon: '📋',
  },
  redteam: {
    name: 'Red Team',
    color: '#ef4444',
    bgColor: '#ef444418',
    icon: '⚡',
  },
  human: {
    name: 'Human',
    color: '#a855f7',
    bgColor: '#a855f718',
    icon: '👤',
  },
};

export const PHASE_LABELS: Record<string, string> = {
  explore: 'EXPLORE',
  debate: 'DEBATE',
  deepen: 'DEEPEN',
  converge: 'CONVERGE',
  synthesis: 'SYNTHESIS',
};

export const STANCE_COLORS: Record<string, string> = {
  supportive: '#22c55e',
  critical: '#ef4444',
  neutral: '#94a3b8',
  novel_connection: '#a855f7',
};

export const TRIGGER_COLORS: Record<string, string> = {
  relevance: '#3b82f6',
  disagreement: '#ef4444',
  question: '#f59e0b',
  silence_breaking: '#94a3b8',
  bridge_opportunity: '#a855f7',
  uncertainty_response: '#06b6d4',
  consensus_forming: '#ef4444',
  criticism_gap: '#f97316',
  premature_convergence: '#f97316',
  seed_phase: '#64748b',
  human_intervention: '#a855f7',
};
