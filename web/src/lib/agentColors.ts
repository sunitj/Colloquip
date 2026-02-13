const PALETTE = [
  '#3B82F6', // blue
  '#22C55E', // green
  '#F59E0B', // amber
  '#8B5CF6', // violet
  '#06B6D4', // cyan
  '#EC4899', // pink
  '#F97316', // orange
  '#14B8A6', // teal
  '#6366F1', // indigo
  '#84CC16', // lime
];

const RED_TEAM_COLOR = '#EF4444';

function hashString(str: string): number {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    const char = str.charCodeAt(i);
    hash = ((hash << 5) - hash) + char;
    hash |= 0;
  }
  return Math.abs(hash);
}

export function getAgentColor(agentType: string, isRedTeam = false): string {
  if (isRedTeam || agentType === 'redteam' || agentType.includes('red_team')) {
    return RED_TEAM_COLOR;
  }
  return PALETTE[hashString(agentType) % PALETTE.length];
}

export function getAgentBgColor(color: string): string {
  return `${color}18`;
}

export function getAgentInitials(displayName: string): string {
  const words = displayName.split(/[\s&]+/).filter(Boolean);
  if (words.length === 0) return '?';
  if (words.length === 1) return words[0].slice(0, 2).toUpperCase();
  return (words[0][0] + words[1][0]).toUpperCase();
}

// Stance colors
export const STANCE_COLORS: Record<string, string> = {
  supportive: '#22C55E',
  critical: '#EF4444',
  neutral: '#94A3B8',
  novel_connection: '#A855F7',
};

// Phase colors and labels
export const PHASE_COLORS: Record<string, string> = {
  explore: '#3B82F6',
  debate: '#EF4444',
  deepen: '#F59E0B',
  converge: '#22C55E',
  synthesis: '#A855F7',
};

export const PHASE_LABELS: Record<string, string> = {
  explore: 'EXPLORE',
  debate: 'DEBATE',
  deepen: 'DEEPEN',
  converge: 'CONVERGE',
  synthesis: 'SYNTHESIS',
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
