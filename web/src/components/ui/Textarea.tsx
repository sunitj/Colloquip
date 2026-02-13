import { forwardRef } from 'react';
import { cn } from '@/lib/utils';

interface TextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {}

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ className, ...props }, ref) => (
    <textarea
      ref={ref}
      className={cn(
        'w-full rounded-xl border border-border-default bg-white px-4 py-3 text-sm text-text-primary',
        'placeholder:text-text-muted',
        'focus:outline-none focus:ring-2 focus:ring-accent/20 focus:border-accent',
        'disabled:opacity-50 disabled:cursor-not-allowed',
        'min-h-[100px] resize-y',
        'transition-all duration-200',
        className,
      )}
      {...props}
    />
  ),
);
Textarea.displayName = 'Textarea';
