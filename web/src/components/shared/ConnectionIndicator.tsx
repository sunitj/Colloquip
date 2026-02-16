interface ConnectionIndicatorProps {
  connected: boolean;
}

export function ConnectionIndicator({ connected }: ConnectionIndicatorProps) {
  return (
    <div className="flex items-center gap-1.5">
      <span
        className="inline-block h-2 w-2 rounded-full"
        style={{ backgroundColor: connected ? '#22C55E' : '#6B7280' }}
      />
      <span className="text-xs text-text-muted">
        {connected ? 'Connected' : 'Standby'}
      </span>
    </div>
  );
}
