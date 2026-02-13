import { useState } from 'react';
import { cn } from '@/lib/utils';

interface TooltipProps {
  content: string;
  children: React.ReactNode;
  className?: string;
}

export function Tooltip({ content, children, className }: TooltipProps) {
  const [show, setShow] = useState(false);

  return (
    <span
      className="relative inline-flex"
      onMouseEnter={() => setShow(true)}
      onMouseLeave={() => setShow(false)}
    >
      {children}
      {show && (
        <span
          className={cn(
            'absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-2 py-1',
            'text-xs text-text-primary bg-bg-elevated border border-border-default rounded-sm',
            'whitespace-nowrap pointer-events-none z-50',
            className,
          )}
          role="tooltip"
        >
          {content}
        </span>
      )}
    </span>
  );
}
