import { Badge } from '@/components/ui/Badge';
import { PHASE_COLORS, PHASE_LABELS } from '@/lib/agentColors';

export function PhaseBadge({ phase }: { phase: string }) {
  const color = PHASE_COLORS[phase] || '#64748B';
  const label = PHASE_LABELS[phase] || phase.toUpperCase();

  return (
    <Badge
      className="border"
      style={{ color, borderColor: `${color}40`, backgroundColor: `${color}15` }}
    >
      {label}
    </Badge>
  );
}
