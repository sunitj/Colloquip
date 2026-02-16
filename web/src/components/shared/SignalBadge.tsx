import { cn } from '@/lib/utils';

interface SignalBadgeProps {
  signal: 'low' | 'medium' | 'high';
  className?: string;
}

const SIGNAL_CONFIG: Record<string, { color: string }> = {
  high: { color: '#EF4444' },
  medium: { color: '#F59E0B' },
  low: { color: '#6B7280' },
};

export function SignalBadge({ signal, className }: SignalBadgeProps) {
  const config = SIGNAL_CONFIG[signal];

  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-bold uppercase tracking-wide',
        className,
      )}
      style={{
        backgroundColor: `${config.color}26`,
        color: config.color,
      }}
    >
      {signal}
    </span>
  );
}
