import { forwardRef } from 'react';
import { cn } from '@/lib/utils';

type ButtonVariant = 'default' | 'ghost' | 'outline' | 'destructive';
type ButtonSize = 'sm' | 'md' | 'lg' | 'icon';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
}

const variantStyles: Record<ButtonVariant, string> = {
  default: 'bg-accent text-white hover:bg-accent-hover',
  ghost: 'bg-transparent hover:bg-bg-tertiary text-text-secondary hover:text-text-primary',
  outline: 'border border-border-default bg-transparent hover:bg-bg-tertiary text-text-secondary hover:text-text-primary',
  destructive: 'bg-error text-white hover:brightness-110',
};

const sizeStyles: Record<ButtonSize, string> = {
  sm: 'h-7 px-3 text-xs',
  md: 'h-9 px-4 text-sm',
  lg: 'h-11 px-6 text-base',
  icon: 'h-9 w-9',
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = 'default', size = 'md', disabled, ...props }, ref) => (
    <button
      ref={ref}
      className={cn(
        'inline-flex items-center justify-center gap-2 rounded-md font-medium transition-colors',
        'focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent',
        'disabled:opacity-50 disabled:pointer-events-none',
        'cursor-pointer',
        variantStyles[variant],
        sizeStyles[size],
        className,
      )}
      disabled={disabled}
      {...props}
    />
  ),
);
Button.displayName = 'Button';
