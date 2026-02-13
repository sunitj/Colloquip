import { Badge } from '@/components/ui/Badge';

const statusConfig: Record<string, { color: string; label: string }> = {
  active: { color: '#3B82F6', label: 'Active' },
  running: { color: '#3B82F6', label: 'Running' },
  pending: { color: '#64748B', label: 'Pending' },
  paused: { color: '#F59E0B', label: 'Paused' },
  completed: { color: '#22C55E', label: 'Completed' },
  failed: { color: '#EF4444', label: 'Failed' },
  cancelled: { color: '#64748B', label: 'Cancelled' },
};

export function StatusBadge({ status }: { status: string }) {
  const config = statusConfig[status] || { color: '#64748B', label: status };
  return (
    <Badge
      style={{ color: config.color, borderColor: `${config.color}40`, backgroundColor: `${config.color}15` }}
      className="border"
    >
      {config.label}
    </Badge>
  );
}
