import { cn } from '@/lib/utils';

interface ThinkingIndicatorProps {
  message?: string;
  className?: string;
}

export function ThinkingIndicator({ message = 'Agents deliberating...', className }: ThinkingIndicatorProps) {
  return (
    <div className={cn('flex items-center gap-3 px-4 py-3 rounded-xl bg-pastel-lavender-bg shadow-sm', className)}>
      <span className="flex gap-1">
        {[0, 1, 2].map((i) => (
          <span
            key={i}
            className="w-1.5 h-1.5 rounded-full bg-pastel-lavender animate-[thinkingBounce_1.4s_ease-in-out_infinite]"
            style={{ animationDelay: `${i * 0.2}s` }}
          />
        ))}
      </span>
      <span className="text-sm text-text-muted">{message}</span>
    </div>
  );
}
