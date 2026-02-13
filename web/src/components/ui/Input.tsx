import { forwardRef } from 'react';
import { cn } from '@/lib/utils';

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ className, ...props }, ref) => (
    <input
      ref={ref}
      className={cn(
        'w-full h-11 rounded-xl border border-border-default bg-white px-4 text-sm text-text-primary',
        'placeholder:text-text-muted',
        'focus:outline-none focus:ring-2 focus:ring-accent/20 focus:border-accent',
        'disabled:opacity-50 disabled:cursor-not-allowed',
        'transition-all duration-200',
        className,
      )}
      {...props}
    />
  ),
);
Input.displayName = 'Input';
