import { Chip } from '@heroui/react';
import { cn } from '@/lib/utils';

type BadgeVariant = 'default' | 'outline' | 'supportive' | 'critical' | 'neutral' | 'novel' | 'phase';

interface BadgeProps {
  variant?: BadgeVariant;
  className?: string;
  children?: React.ReactNode;
  style?: React.CSSProperties;
}

const colorMap: Record<BadgeVariant, string> = {
  default: 'bg-bg-tertiary text-text-secondary',
  outline: 'border border-border-default text-text-secondary bg-transparent',
  supportive: 'bg-pastel-mint-bg text-[#3D9B6E]',
  critical: 'bg-pastel-rose-bg text-[#C95A6B]',
  neutral: 'bg-bg-tertiary text-text-secondary',
  novel: 'bg-pastel-lavender-bg text-[#8B6DBF]',
  phase: 'bg-pastel-lavender-bg text-[#8B6DBF]',
};

export function Badge({ className, variant = 'default', children, style }: BadgeProps) {
  return (
    <Chip
      size="sm"
      style={style}
      className={cn(
        'inline-flex items-center rounded-full px-2.5 py-1 text-xs font-semibold uppercase tracking-wide',
        colorMap[variant],
        className,
      )}
    >
      {children}
    </Chip>
  );
}
