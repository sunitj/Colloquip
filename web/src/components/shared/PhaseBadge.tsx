import { Badge } from '@/components/ui/Badge';
import { PHASE_COLORS, PHASE_LABELS } from '@/lib/agentColors';

export function PhaseBadge({ phase }: { phase: string }) {
  const color = PHASE_COLORS[phase] || '#A0ADB4';
  const label = PHASE_LABELS[phase] || phase;

  return (
    <Badge
      style={{ color, backgroundColor: `${color}18` }}
    >
      {label}
    </Badge>
  );
}
