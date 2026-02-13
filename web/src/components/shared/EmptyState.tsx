import { cn } from '@/lib/utils';

interface EmptyStateProps {
  title: string;
  description?: string;
  action?: React.ReactNode;
  className?: string;
}

export function EmptyState({ title, description, action, className }: EmptyStateProps) {
  return (
    <div className={cn('flex flex-col items-center justify-center py-20 text-center', className)}>
      <svg width="88" height="88" viewBox="0 0 88 88" className="mb-8 opacity-50">
        <circle cx="44" cy="44" r="32" fill="#C7B8EA" opacity="0.3" />
        <circle cx="60" cy="28" r="18" fill="#A8D8EA" opacity="0.3" />
        <circle cx="28" cy="60" r="14" fill="#B5EAD7" opacity="0.3" />
        <circle cx="64" cy="60" r="11" fill="#FFB5C2" opacity="0.3" />
      </svg>
      <p className="text-text-primary text-base font-medium font-[family-name:var(--font-heading)]">{title}</p>
      {description && <p className="text-text-muted text-sm mt-2 max-w-sm">{description}</p>}
      {action && <div className="mt-6">{action}</div>}
    </div>
  );
}
