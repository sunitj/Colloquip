import { cn } from '@/lib/utils';

interface StatusBadgeProps {
  status: string;
  className?: string;
}

const STATUS_CONFIG: Record<string, { color: string; label: string; pulse?: boolean }> = {
  active: { color: '#22C55E', label: 'Active' },
  running: { color: '#22C55E', label: 'Running', pulse: true },
  pending: { color: '#F59E0B', label: 'Pending' },
  completed: { color: 'var(--color-text-muted)', label: 'Completed' },
  failed: { color: '#EF4444', label: 'Failed' },
  cancelled: { color: '#EF4444', label: 'Cancelled' },
  paused: { color: 'var(--color-text-secondary)', label: 'Paused' },
};

export function StatusBadge({ status, className }: StatusBadgeProps) {
  const config = STATUS_CONFIG[status] ?? {
    color: 'var(--color-text-muted)',
    label: status,
  };

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium',
        className,
      )}
      style={{
        backgroundColor: `${config.color}26`,
        color: config.color,
      }}
    >
      {config.pulse && (
        <span className="relative flex h-2 w-2">
          <span
            className="absolute inline-flex h-full w-full animate-ping rounded-full opacity-75"
            style={{ backgroundColor: config.color }}
          />
          <span
            className="relative inline-flex h-2 w-2 rounded-full"
            style={{ backgroundColor: config.color }}
          />
        </span>
      )}
      {config.label}
    </span>
  );
}
