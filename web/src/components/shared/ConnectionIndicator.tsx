import { cn } from '@/lib/utils';

export function ConnectionIndicator({ connected }: { connected: boolean }) {
  return (
    <div className={cn('flex items-center gap-1.5 text-[10px]', connected ? 'text-success' : 'text-text-muted')}>
      <span className={cn('w-1.5 h-1.5 rounded-full', connected ? 'bg-success animate-pulse' : 'bg-text-muted')} />
      {connected ? 'Connected' : 'Disconnected'}
    </div>
  );
}
