import { cn } from '@/lib/utils';

interface TabsProps {
  value: string;
  onValueChange: (value: string) => void;
  children: React.ReactNode;
  className?: string;
}

export function Tabs({ className, children }: TabsProps) {
  return <div className={cn('', className)}>{children}</div>;
}

interface TabsListProps extends React.HTMLAttributes<HTMLDivElement> {}

export function TabsList({ className, ...props }: TabsListProps) {
  return (
    <div
      className={cn(
        'inline-flex items-center gap-0.5 rounded-md bg-bg-tertiary p-0.5',
        className,
      )}
      role="tablist"
      {...props}
    />
  );
}

interface TabsTriggerProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  value: string;
  active?: boolean;
}

export function TabsTrigger({ className, active, ...props }: TabsTriggerProps) {
  return (
    <button
      role="tab"
      aria-selected={active}
      className={cn(
        'px-3 py-1.5 text-xs font-semibold uppercase tracking-wide rounded-sm transition-colors cursor-pointer',
        active
          ? 'bg-bg-secondary text-text-primary'
          : 'text-text-muted hover:text-text-secondary',
        className,
      )}
      {...props}
    />
  );
}
