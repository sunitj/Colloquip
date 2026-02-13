import { Tooltip as HeroTooltip } from '@heroui/react';
import { cn } from '@/lib/utils';

interface TooltipProps {
  content: string;
  children: React.ReactNode;
  className?: string;
}

export function Tooltip({ content, children, className }: TooltipProps) {
  return (
    <HeroTooltip delay={300}>
      <HeroTooltip.Trigger>
        {children}
      </HeroTooltip.Trigger>
      <HeroTooltip.Content
        className={cn(
          'px-3 py-2 text-xs text-text-primary bg-bg-secondary border border-border-default shadow-md rounded-lg z-50',
          className,
        )}
      >
        {content}
      </HeroTooltip.Content>
    </HeroTooltip>
  );
}
