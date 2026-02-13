import { Badge } from '@/components/ui/Badge';

const statusConfig: Record<string, { color: string; bg: string; label: string }> = {
  active: { color: '#7CB9E8', bg: '#EDF6FA', label: 'Active' },
  running: { color: '#7CB9E8', bg: '#EDF6FA', label: 'Running' },
  pending: { color: '#A0ADB4', bg: '#F8F9FA', label: 'Pending' },
  paused: { color: '#F0C060', bg: '#FFFBEC', label: 'Paused' },
  completed: { color: '#5EBD8A', bg: '#EDFAF4', label: 'Completed' },
  failed: { color: '#E8788A', bg: '#FFF0F3', label: 'Failed' },
  cancelled: { color: '#A0ADB4', bg: '#F8F9FA', label: 'Cancelled' },
};

export function StatusBadge({ status }: { status: string }) {
  const config = statusConfig[status] || { color: '#A0ADB4', bg: '#F8F9FA', label: status };
  return (
    <Badge
      style={{ color: config.color, backgroundColor: config.bg }}
    >
      {config.label}
    </Badge>
  );
}
