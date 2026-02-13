import { cn } from '@/lib/utils';

interface PageHeaderProps {
  title: string;
  subtitle?: string;
  actions?: React.ReactNode;
  breadcrumb?: React.ReactNode;
  className?: string;
}

export function PageHeader({ title, subtitle, actions, breadcrumb, className }: PageHeaderProps) {
  return (
    <div className={cn('mb-6', className)}>
      {breadcrumb && <div className="mb-2">{breadcrumb}</div>}
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-text-primary">{title}</h1>
          {subtitle && <p className="text-sm text-text-secondary mt-0.5">{subtitle}</p>}
        </div>
        {actions && <div className="flex items-center gap-2 shrink-0">{actions}</div>}
      </div>
    </div>
  );
}
