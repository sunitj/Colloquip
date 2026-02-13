import { cn } from '@/lib/utils';
import { Tooltip } from '@/components/ui/Tooltip';

export function ConnectionIndicator({ connected }: { connected: boolean }) {
  const indicator = (
    <div className={cn('flex items-center gap-2 text-xs', connected ? 'text-[#3D9B6E]' : 'text-text-muted')}>
      <span className={cn('w-2 h-2 rounded-full', connected ? 'bg-pastel-mint' : 'bg-bg-tertiary')} />
      {connected ? 'Connected' : 'Standby'}
    </div>
  );

  if (!connected) {
    return (
      <Tooltip content="WebSocket connects during active deliberations">
        {indicator}
      </Tooltip>
    );
  }

  return indicator;
}
