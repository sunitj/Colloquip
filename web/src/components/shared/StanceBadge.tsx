import { cn } from '@/lib/utils';
import { STANCE_COLORS } from '@/lib/agentColors';

interface StanceBadgeProps {
  stance: string;
  className?: string;
}

const STANCE_LABELS: Record<string, string> = {
  supportive: 'Supportive',
  critical: 'Critical',
  neutral: 'Neutral',
  novel_connection: 'Novel',
};

export function StanceBadge({ stance, className }: StanceBadgeProps) {
  const color = STANCE_COLORS[stance] ?? '#6B7280';
  const label = STANCE_LABELS[stance] ?? stance;

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
