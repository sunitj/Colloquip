import { cn } from '@/lib/utils';

interface ThinkingIndicatorProps {
  message?: string;
  className?: string;
}

export function ThinkingIndicator({ message = 'Agents deliberating...', className }: ThinkingIndicatorProps) {
  return (
    <div className={cn('flex items-center gap-3 px-4 py-3 rounded-lg bg-bg-tertiary/50', className)}>
      <span className="flex gap-1">
        {[0, 1, 2].map((i) => (
          <span
            key={i}
            className="w-1.5 h-1.5 rounded-full bg-accent animate-pulse"
            style={{ animationDelay: `${i * 0.2}s` }}
          />
        ))}
      </span>
      <span className="text-sm text-text-muted">{message}</span>
    </div>
  );
}
