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
        'inline-flex items-center gap-1 border-b border-border-default',
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
        'px-4 py-2.5 text-sm font-medium transition-all duration-200 cursor-pointer -mb-px',
        active
          ? 'text-text-primary border-b-2 border-accent'
          : 'text-text-muted hover:text-text-secondary',
        className,
      )}
      {...props}
    />
  );
}
