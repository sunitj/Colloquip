import { Badge } from '@/components/ui/Badge';
import type { AgentStance } from '@/types/deliberation';

const variantMap: Record<string, 'supportive' | 'critical' | 'neutral' | 'novel'> = {
  supportive: 'supportive',
  critical: 'critical',
  neutral: 'neutral',
  novel_connection: 'novel',
};

export function StanceBadge({ stance }: { stance: AgentStance | string }) {
  const variant = variantMap[stance] || 'neutral';
  return <Badge variant={variant}>{stance.replace(/_/g, ' ')}</Badge>;
}
