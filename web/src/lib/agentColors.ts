const PALETTE = [
  '#7CB9E8', // pastel sky blue
  '#B5EAD7', // pastel mint
  '#FFD4A8', // pastel peach
  '#C7B8EA', // pastel lavender
  '#A8D8EA', // pastel cyan
  '#FFB5C2', // pastel rose
  '#FFEAA0', // pastel lemon
  '#B5D8B5', // pastel sage
  '#DDB8F0', // pastel lilac
  '#B8D4E3', // pastel steel blue
];

const PALETTE_TEXT = [
  '#3B7AB5', // sky text
  '#3D9B6E', // mint text
  '#C87E3A', // peach text
  '#7B5EAF', // lavender text
  '#3B8BA5', // cyan text
  '#C95A6B', // rose text
  '#B5960A', // lemon text
  '#4A8A4A', // sage text
  '#9B5EBF', // lilac text
  '#3B6E8A', // steel text
];

const RED_TEAM_COLOR = '#E8788A';
const RED_TEAM_TEXT = '#C95A6B';

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
  if (isRedTeam || agentType === 'redteam' || agentType.includes('red_team')) {
    return RED_TEAM_TEXT;
  }
  return PALETTE_TEXT[hashString(agentType) % PALETTE_TEXT.length];
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

// Stance colors -- pastelized
export const STANCE_COLORS: Record<string, string> = {
  supportive: '#5EBD8A',
  critical: '#E8788A',
  neutral: '#A0ADB4',
  novel_connection: '#A78BDE',
};

// Phase colors -- pastelized
export const PHASE_COLORS: Record<string, string> = {
  explore: '#7CB9E8',
  debate: '#E8788A',
  deepen: '#F0C060',
  converge: '#5EBD8A',
  synthesis: '#B49ADE',
};

export const PHASE_LABELS: Record<string, string> = {
  explore: 'Explore',
  debate: 'Debate',
  deepen: 'Deepen',
  converge: 'Converge',
  synthesis: 'Synthesis',
};

export const TRIGGER_COLORS: Record<string, string> = {
  relevance: '#7CB9E8',
  disagreement: '#E8788A',
  question: '#F0C060',
  silence_breaking: '#A0ADB4',
  bridge_opportunity: '#A78BDE',
  uncertainty_response: '#A8D8EA',
  consensus_forming: '#5EBD8A',
  criticism_gap: '#FFD4A8',
  premature_convergence: '#FFD4A8',
  seed_phase: '#A0ADB4',
  human_intervention: '#C7B8EA',
};
