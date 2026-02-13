import { cn } from '@/lib/utils';
import { PHASE_COLORS, PHASE_LABELS } from '@/lib/agentColors';

interface PhaseBadgeProps {
  phase: string;
  className?: string;
}

export function PhaseBadge({ phase, className }: PhaseBadgeProps) {
  const color = PHASE_COLORS[phase] ?? '#6B7280';
  const label = PHASE_LABELS[phase] ?? phase;

  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium',
        className,
      )}
      style={{
        backgroundColor: `${color}26`,
        color,
      }}
    >
      {label}
    </span>
  );
}
