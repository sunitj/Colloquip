import { formatCost } from '@/lib/utils';

export function CostDisplay({ cost, className }: { cost: number; className?: string }) {
  return (
    <span className={`font-mono text-xs text-text-muted ${className || ''}`}>
      {formatCost(cost)}
    </span>
  );
}
