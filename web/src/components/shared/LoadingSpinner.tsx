import { cn } from '@/lib/utils';

export function LoadingSpinner({ className }: { className?: string }) {
  return (
    <div className={cn('w-5 h-5 border-2 border-border-default border-t-accent rounded-full animate-spin', className)} />
  );
}
