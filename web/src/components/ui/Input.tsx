import { forwardRef } from 'react';
import { cn } from '@/lib/utils';

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ className, ...props }, ref) => (
    <input
      ref={ref}
      className={cn(
        'w-full rounded-md border border-border-default bg-bg-tertiary px-3 py-2 text-sm text-text-primary',
        'placeholder:text-text-muted',
        'focus:outline-none focus:border-accent',
        'disabled:opacity-50 disabled:cursor-not-allowed',
        className,
      )}
      {...props}
    />
  ),
);
Input.displayName = 'Input';
