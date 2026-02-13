import { forwardRef } from 'react';
import { cn } from '@/lib/utils';

interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {}

export const Select = forwardRef<HTMLSelectElement, SelectProps>(
  ({ className, children, ...props }, ref) => (
    <select
      ref={ref}
      className={cn(
        'h-11 rounded-xl border border-border-default bg-white px-4 text-sm text-text-primary',
        'focus:outline-none focus:ring-2 focus:ring-accent/20 focus:border-accent',
        'disabled:opacity-50 disabled:cursor-not-allowed',
        'transition-all duration-200',
        className,
      )}
      {...props}
    >
      {children}
    </select>
  ),
);
Select.displayName = 'Select';
