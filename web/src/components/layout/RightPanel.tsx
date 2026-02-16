import { cn } from '@/lib/utils';

interface RightPanelProps {
  children: React.ReactNode;
  className?: string;
}

export function RightPanel({ children, className }: RightPanelProps) {
  return (
    <aside
      className={cn(
        'hidden lg:flex lg:flex-col w-[var(--right-panel-width)] shrink-0 bg-bg-surface border-l border-border-default overflow-y-auto p-5',
        className
      )}
    >
      {children}
    </aside>
  );
}
