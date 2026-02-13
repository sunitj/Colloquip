import { cn } from '@/lib/utils';

interface RightPanelProps {
  children: React.ReactNode;
  className?: string;
}

export function RightPanel({ children, className }: RightPanelProps) {
  return (
    <aside className={cn('w-[var(--right-panel-width)] shrink-0 border-l border-border-default overflow-y-auto p-4 space-y-4', className)}>
      {children}
    </aside>
  );
}
