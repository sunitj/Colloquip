// Vibrant palette optimized for dark backgrounds
const PALETTE = [
  '#34D399', // emerald
  '#60A5FA', // sky
  '#FBBF24', // amber
  '#A78BFA', // violet
  '#F472B6', // pink
  '#2DD4BF', // teal
  '#FB923C', // orange
  '#C084FC', // purple
  '#818CF8', // indigo
  '#22D3EE', // cyan
];

export const RED_TEAM_COLOR = '#F87171';

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

export function getAgentTextColor(agentType: string, isRedTeam = false): string {
  // On dark backgrounds, the vibrant palette colors are legible as-is
  if (isRedTeam || agentType === 'redteam' || agentType.includes('red_team')) {
    return RED_TEAM_COLOR;
  }
  return PALETTE[hashString(agentType) % PALETTE.length];
}

export function getAgentBgColor(color: string): string {
  // 15% opacity hex suffix = 26
  return `${color}26`;
}

export function getAgentInitials(displayName: string): string {
  const words = displayName.split(/[\s&]+/).filter(Boolean);
  if (words.length === 0) return '?';
  if (words.length === 1) return words[0].slice(0, 2).toUpperCase();
  return (words[0][0] + words[1][0]).toUpperCase();
}

// Stance colors -- vibrant for dark theme
export const STANCE_COLORS: Record<string, string> = {
  supportive: '#22C55E',
  critical: '#EF4444',
  neutral: '#6B7280',
  novel_connection: '#A855F7',
};

// Phase colors -- vibrant for dark theme
export const PHASE_COLORS: Record<string, string> = {
  explore: '#3B82F6',
  debate: '#EF4444',
  deepen: '#F59E0B',
  converge: '#22C55E',
  synthesis: '#A855F7',
};

export const PHASE_LABELS: Record<string, string> = {
  explore: 'Explore',
  debate: 'Debate',
  deepen: 'Deepen',
  converge: 'Converge',
  synthesis: 'Synthesis',
};

export const TRIGGER_COLORS: Record<string, string> = {
  relevance: '#3B82F6',
  disagreement: '#EF4444',
  question: '#F59E0B',
  silence_breaking: '#6B7280',
  bridge_opportunity: '#A855F7',
  uncertainty_response: '#22D3EE',
  consensus_forming: '#22C55E',
  criticism_gap: '#FB923C',
  premature_convergence: '#FBBF24',
  seed_phase: '#94A3B8',
  human_intervention: '#818CF8',
};
