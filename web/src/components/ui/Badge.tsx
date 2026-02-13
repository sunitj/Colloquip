import { cn } from '@/lib/utils';

type BadgeVariant = 'default' | 'outline' | 'supportive' | 'critical' | 'neutral' | 'novel' | 'phase';

interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: BadgeVariant;
}

const variantStyles: Record<BadgeVariant, string> = {
  default: 'bg-bg-tertiary text-text-secondary',
  outline: 'border border-border-default text-text-secondary bg-transparent',
  supportive: 'bg-stance-supportive/15 text-stance-supportive border border-stance-supportive/30',
  critical: 'bg-stance-critical/15 text-stance-critical border border-stance-critical/30',
  neutral: 'bg-stance-neutral/15 text-stance-neutral border border-stance-neutral/30',
  novel: 'bg-stance-novel/15 text-stance-novel border border-stance-novel/30',
  phase: 'bg-accent/15 text-accent border border-accent/30',
};

export function Badge({ className, variant = 'default', ...props }: BadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-sm px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide',
        variantStyles[variant],
        className,
      )}
      {...props}
    />
  );
}
